"""MCP launch/provenance guard for the checkout containing this script."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import queue
import time
from collections import deque
from mcp_backend import Backend, PersistentBackend
from resource_guard import Relay, MCPOutput, cached_control, complete_catalogue, backend_work, IDLE_SECONDS, CancelledError

from xray_analysis import ROOT, TOOLS, build_env, cache_root, graph_status, node_executable, source_state, refresh_graph, remaining

# Leave headroom under the configured 60s client startup limit. The watchdog
# also bounds blocking filesystem calls and nested gopls adapter startup.
STARTUP_SECONDS = 45
REQUEST_SECONDS = 60
GRAPH_SECONDS = 210
# Graph work plus forced retirement stays below the client's 240s tool limit.
CANCEL_RETIRE_SECONDS = 15
lock = threading.Lock()
catalogue = None
catalogue_revision = 0


def emit(message):
    global catalogue, catalogue_revision
    if message.get('method')=='notifications/tools/list_changed':
        with lock:
            catalogue=None;catalogue_revision+=1
            output.emit(message)
        return
    output.emit(message)


def decorate(message, method):
        if method == 'initialize':
            remaining(startup_deadline, 'frontend initialization')
            startup_complete.set()
        if method == "tools/list" and "result" in message:
            read_tools = {"go_workspace", "go_search", "go_file_context", "go_package_api", "go_symbol_references", "go_diagnostics",
                          "list_repos", "query", "context", "impact", "trace", "check"}
            for tool in message["result"].get("tools", []):
                if tool.get("name") in read_tools:
                    tool.setdefault("annotations", {}).update(readOnlyHint=True, destructiveHint=False)
        if method == "initialize" and "result" in message:
            instructions = message["result"].get("instructions", "")
            instructions += "\nXray checkout: " + str(ROOT) + ". Validate source/build provenance before change-impact claims. "
            if args.backend == "gopls":
                instructions += "Profile: " + args.profile + ", CGO=0, no extra tags. Use this server only for that build; use the checkout-scoped CLI for other tags."
            else:
                instructions += "Graph calls require a matching committed-source manifest. Missing/stale committed-source indexes refresh automatically on the first query. Dirty-source requests fail explicitly; use live gopls. Graph calls reuse a backend for the current immutable manifest; no manual reconnect is required. Equal fingerprints permit reuse across documentation-only HEAD changes. Graph edges are mixed-platform and incomplete."
            message["result"]["instructions"] = instructions
        return message


def graph_backend(key, deadline=None, cancelled=None):
    registry, index = key
    current_env = env.copy()
    current_env.update(GITNEXUS_HOME=registry, GITNEXUS_STORAGE_PATH=index)
    return Backend(command, ROOT, current_env, sys.stderr, notify=emit, deadline=deadline, cancelled=cancelled)


def graph_request(message, manifest, deadline=None, cancelled=None):
    """Reuse the backend until the immutable index generation changes."""
    result = graph_session.call((manifest["registry_home"], manifest["index"]), message, deadline=deadline, cancelled=cancelled)
    after = graph_status(deadline=deadline, cancelled=cancelled)
    if after["status"] != "CURRENT" or after["manifest"]["index"] != manifest["index"]:
        graph_session.close()
        raise RuntimeError("Source/index changed during graph query")
    if "result" in result and isinstance(result["result"], dict) and "content" in result["result"]:
        result["result"]["content"].append({"type": "text", "text": json.dumps({"xray_provenance": {"repo": str(ROOT), "source_head": manifest["head"], "validated_head": after["source"]["head"], "fingerprint": manifest["fingerprint"], "coverage": manifest["coverage"]}})})
    if deadline is not None:remaining(deadline,'graph response validation',cancelled=cancelled)
    return result

def handle_request(message, deadline, cancelled):
    """Only the one operation worker may access the generation-owned backend."""
    global catalogue
    method = message.get('method')
    try:
        remaining(deadline,'request admission',cancelled=cancelled)
        if method in ('tools/call','resources/read'):
            current = graph_status(deadline=deadline, cancelled=cancelled)
            if current['status'] != 'CURRENT' and not current['source']['dirty']:
                current = refresh_graph(deadline=deadline, cancelled=cancelled)
            if current['status'] != 'CURRENT':
                raise RuntimeError('STALE_INDEX: ' + current['status'] + '. Use live gopls for dirty source.')
            result = graph_request(message,current['manifest'],deadline=deadline,cancelled=cancelled)
        elif method == 'initialize':
            key = (env['GITNEXUS_HOME'],env['GITNEXUS_STORAGE_PATH'])
            request = {'jsonrpc':'2.0','id':'catalogue','method':'tools/list'}
            revision = catalogue_revision
            inventory = graph_session.call(key,request,deadline=deadline,cancelled=cancelled)
            with lock:
                if complete_catalogue(request,inventory) and revision == catalogue_revision:catalogue = inventory['result']
            result = {**graph_session.backend.initialization,'id':message['id']}
        else:
            key = graph_session.key or (env['GITNEXUS_HOME'],env['GITNEXUS_STORAGE_PATH'])
            revision = catalogue_revision
            result = graph_session.call(key,message,deadline=deadline,cancelled=cancelled)
            with lock:
                if complete_catalogue(message,result) and revision == catalogue_revision:catalogue = result['result']
        return decorate(result,method)
    except (RuntimeError, TimeoutError, queue.Empty, OSError, subprocess.SubprocessError) as error:
        graph_session.close(force=cancelled.is_set())
        result = {'jsonrpc':'2.0','id':message.get('id'),'error':{'code':-32800 if isinstance(error,CancelledError) else -32001,'message':str(error)}}
        return decorate(result,method)


def serve_graph():
    events = queue.Queue(maxsize=64)
    pending = deque()
    active = None
    last_activity = time.monotonic()
    def inputs():
        try:
            for line in sys.stdin:
                try:events.put(('client',time.monotonic(),json.loads(line)))
                except ValueError:continue
        finally:events.put(('client',0,None))
    threading.Thread(target=inputs,daemon=True).start()
    def start(operation):
        def work():
            try:
                response = handle_request(operation['message'],operation['deadline'],operation['cancelled'])
            except Exception as error:
                # Malformed backend/source data must release the one worker slot.
                # Backend lifetime remains owned by this worker, never stdin.
                try:graph_session.close(force=True)
                except Exception:os._exit(124)
                response = {'jsonrpc':'2.0','id':operation['message']['id'],
                            'error':{'code':-32603,'message':'MCP operation failed: '+str(error)}}
            events.put(('done',operation,response))
        operation['thread'] = threading.Thread(target=work,daemon=True)
        operation['thread'].start()
    def cancelled_response(message):
        emit({'jsonrpc':'2.0','id':message['id'],'error':{'code':-32800,'message':'MCP operation cancelled'}})
    try:
        while True:
            now = time.monotonic()
            for operation in list(pending):
                if now >= operation['deadline']:
                    pending.remove(operation)
                    emit({'jsonrpc':'2.0','id':operation['message']['id'],
                          'error':{'code':-32001,'message':'MCP request exceeded total deadline while queued'}})
            if active and now >= active['deadline'] and not active['cancelled'].is_set():
                active['cancelled'].set()
                active['retire_deadline'] = now+CANCEL_RETIRE_SECONDS
                emit({'jsonrpc':'2.0','id':active['message']['id'],
                      'error':{'code':-32001,'message':'MCP request exceeded total deadline'}})
            if active and active['cancelled'].is_set() and now >= active['retire_deadline']:
                # A blocked Python/filesystem call cannot safely be detached from
                # graph_session. Retire this frontend and its owned descendants.
                os._exit(124)
            if active is None and pending:
                active = pending.popleft()
                start(active)
            if active is None and time.monotonic()-last_activity >= IDLE_SECONDS:
                graph_session.close()
                last_activity = time.monotonic()
            try:side, marker, message = events.get(timeout=.1)
            except queue.Empty:continue
            if side == 'done':
                marker['thread'].join()
                if not marker['cancelled'].is_set():emit(message)
                if backend_work(marker['message'].get('method')):last_activity = time.monotonic()
                active = None
                continue
            if message is None:break
            method = message.get('method')
            if method == 'notifications/cancelled':
                target = message.get('params',{}).get('requestId')
                if target is None:continue
                if active and active['message']['id'] == target and active['message'].get('method') != 'initialize':
                    if not active['cancelled'].is_set():
                        active['cancelled'].set()
                        active['retire_deadline'] = time.monotonic()+CANCEL_RETIRE_SECONDS
                        cancelled_response(active['message'])
                else:
                    for operation in list(pending):
                        if operation['message']['id'] == target and operation['message'].get('method') != 'initialize':
                            pending.remove(operation)
                            cancelled_response(operation['message'])
                            break
                continue
            with lock:control = cached_control(message,catalogue)
            if control is not None:
                emit(decorate(control,method))
                continue
            if 'id' not in message:continue
            if len(pending) >= 32:
                emit({'jsonrpc':'2.0','id':message['id'],'error':{'code':-32001,'message':'MCP operation queue limit exceeded'}})
                continue
            deadline = startup_deadline if method == 'initialize' else marker+(GRAPH_SECONDS if method in ('tools/call','resources/read') else REQUEST_SECONDS)
            pending.append({'message':message,'deadline':deadline,'cancelled':threading.Event()})
    finally:
        if active:
            active['cancelled'].set()
            active['thread'].join(timeout=CANCEL_RETIRE_SECONDS)
            if active['thread'].is_alive():os._exit(124)
        graph_session.close()


def main(argv=None):
    global args, env, command, output, graph_session, startup_deadline, startup_complete
    startup_deadline = time.monotonic()+STARTUP_SECONDS
    startup_complete = threading.Event()
    def startup_watchdog():
        if not startup_complete.wait(max(0,startup_deadline-time.monotonic())):
            # Supervisor owner-watchers reap only this frontend's descendants.
            os._exit(124)
    threading.Thread(target=startup_watchdog,daemon=True).start()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backend',choices=('gopls','gitnexus'))
    parser.add_argument('--profile',choices=('windows','android','linux'),default='windows')
    parser.add_argument('--repo',type=Path,default=ROOT,help='Assert the installed checkout root')
    parser.add_argument('--identity',action='store_true',help='Read checkout/profile identity without starting a backend')
    args = parser.parse_args(argv)
    if args.repo.resolve() != ROOT.resolve():
        parser.error('--repo must match this installed checkout')
    initial_state = source_state(deadline=startup_deadline)
    if args.identity:
        startup_complete.set()
        print(json.dumps({'source':initial_state,'profile':args.profile,'backend':args.backend,'tools':str(TOOLS)},indent=2))
        return
    env = os.environ.copy()
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
    if args.backend == 'gopls':
        env = build_env(args.profile)
        binary = TOOLS/'bin'/('gopls.exe' if os.name == 'nt' else 'gopls')
        command = [sys.executable,str(ROOT/'.agents/scripts/go_mcp.py'),'--binary',str(binary),'--root',str(ROOT)]
        Relay(command,ROOT,env,transform=decorate).serve()
        return
    state = graph_status(deadline=startup_deadline)
    manifest = state.get('manifest',{})
    env.update(GITNEXUS_HOME=manifest.get('registry_home',str(cache_root()/'empty-registry')),
               GITNEXUS_STORAGE_PATH=manifest.get('index',str(cache_root()/'missing-index')),
               GITNEXUS_MCP_READ_ONLY='1',SCARF_ANALYTICS='false')
    command = [node_executable(),str(TOOLS/'gitnexus/node_modules/gitnexus/dist/cli/index.js'),'mcp']
    output = MCPOutput()
    graph_session = PersistentBackend(graph_backend,deadline_factory=True)
    try:serve_graph()
    finally:
        startup_complete.set()
        output.close()


if __name__ == '__main__':
    main()
