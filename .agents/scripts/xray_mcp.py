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
import copy
import uuid
from collections import deque
from mcp_backend import Backend, PersistentBackend
from resource_guard import Relay, MCPOutput, cached_control, complete_catalogue, backend_work, IDLE_SECONDS, CancelledError

from xray_analysis import ROOT, TOOLS, build_env, cache_root, graph_status, node_executable, source_state, refresh_graph, remaining, graph_key, GRAPH_PREPARE_SECONDS, GRAPH_PREPARE_MAX_SECONDS

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

LOCAL_TOOLS = [
    {'name': 'graph_prepare', 'description': 'Prepare or join the committed graph in a separately bounded owned operation; then graph_wait. No semantic result is implied.', 'inputSchema': {'type': 'object', 'properties': {'force': {'type': 'boolean'}, 'timeout_seconds': {'type': 'number', 'minimum': 1, 'maximum': GRAPH_PREPARE_MAX_SECONDS}}}},
    {'name': 'graph_status', 'description': 'Validate graph source/analyzer readiness and inspect owned preparation progress.', 'inputSchema': {'type': 'object', 'properties': {}}},
    {'name': 'graph_wait', 'description': 'Wait at most 30 seconds. Supply the cold query ticket to execute its exact original call when ready and return the actual result.', 'inputSchema': {'type': 'object', 'properties': {'ticket': {'type': 'string'}, 'preparation_id': {'type': 'string'}, 'timeout_seconds': {'type': 'number', 'minimum': 0, 'maximum': 30}}}},
    {'name': 'graph_cancel', 'description': 'Cancel this frontend owned preparation by its exact ID; never cancels another frontend owner.', 'inputSchema': {'type': 'object', 'properties': {'preparation_id': {'type': 'string'}}, 'required': ['preparation_id']}}
]

def tool_result(message, value):
    return {'jsonrpc': '2.0', 'id': message['id'], 'result': {'content': [{'type': 'text', 'text': json.dumps(value)}], 'structuredContent': value}}


class GraphPreparation:
    """One frontend-owned refresh, using the existing cross-session checkout lease."""
    def __init__(self):
        self.mutex = threading.Lock()
        self.lifecycle = threading.RLock()
        self.thread = None
        self.cancelled = threading.Event()
        self.done = threading.Event()
        self.value = {}
        self.key = None
        self.retire_deadline = None

    def snapshot(self):
        with self.mutex:
            value = copy.deepcopy(self.value)
        if value.get('status') == 'PREPARING':
            value['elapsed_seconds'] = round(time.monotonic()-self.started, 3)
        return value

    def start(self, current, force=False, seconds=GRAPH_PREPARE_SECONDS):
        with self.lifecycle:return self._start(current, force, seconds)

    def _start(self, current, force, seconds):
        key = graph_key(current)
        if self.thread and self.thread.is_alive():
            if key != self.key:
                raise RuntimeError('Source/analyzer changed during preparation; cancel or await the owned preparation before retrying')
            return self.snapshot()
        if self.thread and key == self.key and not force and self.value.get('status') == 'FAILED':
            return self.snapshot()
        if current['source'].get('dirty') or current['source'].get('uncovered_go') or current['source'].get('workspace_files'):
            raise RuntimeError('Graph preparation requires clean committed covered source; use live gopls/AST for dirty or uncovered source')
        if current['status'] == 'CURRENT' and not force:
            return {'status': 'CURRENT', 'identity': key}
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.retire_deadline = None
        self.cancelled = threading.Event()
        self.done = threading.Event()
        self.key = key
        self.value = {'status': 'PREPARING', 'preparation_id': uuid.uuid4().hex,
                      'phase': 'starting', 'identity': key, 'budget_seconds': seconds}
        def progress(value):
            with self.mutex:
                self.value.update(phase=value.get('phase'), owner=value)
        def work():
            try:
                ready = refresh_graph(deadline=self.deadline, cancelled=self.cancelled, force=force, progress=progress)
                if ready.get('status') != 'CURRENT' or graph_key(ready) != key:
                    raise RuntimeError('Source/analyzer changed during graph preparation')
                with self.mutex:self.value.update(status='CURRENT', phase='ready')
            except BaseException as error:
                with self.mutex:self.value.update(status='CANCELLED' if isinstance(error, CancelledError) else 'FAILED', phase='cancelled' if isinstance(error, CancelledError) else 'failed', error=str(error))
            finally:
                self.done.set()
        self.thread = threading.Thread(target=work, daemon=True)
        self.thread.start()
        return self.snapshot()

    def cancel(self, identity):
        with self.lifecycle:return self._cancel(identity)

    def _cancel(self, identity):
        if identity != self.value.get('preparation_id'):
            raise RuntimeError('Unknown frontend preparation_id; another frontend owner cannot be cancelled here')
        self.cancelled.set()
        if self.retire_deadline is None:self.retire_deadline = time.monotonic()+CANCEL_RETIRE_SECONDS
        return self.snapshot()

    def watchdog(self):
        with self.lifecycle:self._watchdog()

    def _watchdog(self):
        if self.thread and self.thread.is_alive():
            if time.monotonic() >= self.deadline and not self.cancelled.is_set():
                self.cancel(self.value['preparation_id'])
            if self.retire_deadline and time.monotonic() >= self.retire_deadline:
                os._exit(124)

    def close(self):
        if self.thread and self.thread.is_alive():
            self.cancel(self.value['preparation_id'])
            self.thread.join(timeout=CANCEL_RETIRE_SECONDS)
            if self.thread.is_alive():os._exit(124)


def bounded_number(arguments, name, default, lower, upper):
    value = arguments.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= value <= upper:
        raise RuntimeError(name + ' must be between ' + str(lower) + ' and ' + str(upper))
    return value


def graph_control(message, deadline, cancelled):
    params = message.get('params', {})
    name = params.get('name')
    arguments = params.get('arguments', {})
    if name == 'graph_status':
        current = graph_status(deadline=deadline, cancelled=cancelled)
        return tool_result(message, {**current, 'frontend_preparation': preparation.snapshot()})
    if name == 'graph_cancel':
        return tool_result(message, preparation.cancel(arguments.get('preparation_id')))
    if name == 'graph_prepare':
        force = arguments.get('force', False)
        if not isinstance(force, bool):raise RuntimeError('force must be boolean')
        seconds = bounded_number(arguments, 'timeout_seconds', args.graph_prepare_seconds, 1, GRAPH_PREPARE_MAX_SECONDS)
        return tool_result(message, preparation.start(graph_status(deadline=deadline, cancelled=cancelled), force=force, seconds=seconds))
    if name != 'graph_wait':return None
    ticket = arguments.get('ticket')
    original = tickets.get(ticket) if ticket is not None else None
    if ticket is not None and original is None:raise RuntimeError('Unknown query ticket for this frontend')
    if original and 'response' in original:
        response = copy.deepcopy(original['response'])
        response['id'] = message['id']
        evidence = {'xray_ticket': {'ticket': ticket, 'cached': True, 'historical': True, 'identity': original['identity']}}
        if 'result' in response:
            response['result'].setdefault('content', []).append({'type': 'text', 'text': json.dumps(evidence)})
        else:response['error']['data'] = evidence
        return response
    def terminal(status, error, progress=None):
        response = tool_result(message, {**(progress or {}), 'status': status, 'error': error,
                    **({'ticket': ticket, 'original_call': original['message'].get('params', {})} if original else {})})
        if original is not None:original['response'] = copy.deepcopy(response)
        return response
    identity = arguments.get('preparation_id', original['preparation_id'] if original else None)
    if identity is not None and identity != preparation.snapshot().get('preparation_id'):
        return terminal('STALE', 'Unknown or replaced frontend preparation_id')
    seconds = bounded_number(arguments, 'timeout_seconds', 20, 0, 30)
    until = min(deadline, time.monotonic()+seconds)
    while preparation.thread and preparation.thread.is_alive() and time.monotonic() < until:
        remaining(deadline, 'preparation wait', cancelled=cancelled)
        preparation.done.wait(min(.1, max(0, until-time.monotonic())))
    remaining(deadline, 'preparation wait', cancelled=cancelled)
    progress = preparation.snapshot()
    if identity is not None and identity != progress.get('preparation_id'):
        return terminal('STALE', 'Preparation changed while waiting; original operation is no longer active')
    if progress.get('status') != 'CURRENT':
        if progress.get('status') in ('FAILED', 'CANCELLED'):
            return terminal(progress['status'], progress.get('error', 'Graph preparation cancelled'), progress)
        return tool_result(message, {**progress, **({'ticket': ticket} if ticket else {})})
    current = graph_status(deadline=deadline, cancelled=cancelled)
    if current['status'] != 'CURRENT':return terminal('STALE', 'Graph changed after preparation; no original query was executed')
    if original is None:return tool_result(message, current)
    if graph_key(current) != original['identity']:
        return terminal('STALE', 'Source/analyzer changed since query admission; ticket cannot run against another identity')
    if 'response' not in original:
        original['response'] = graph_request({**original['message'], 'id': message['id']}, current['manifest'], deadline=deadline, cancelled=cancelled)
    return {**copy.deepcopy(original['response']), 'id': message['id']}


def cold_query(message, current):
    for token in list(tickets):
        if len(tickets) < 32:break
        if 'response' in tickets[token]:del tickets[token]
    if len(tickets) >= 32:raise RuntimeError('Pending graph query ticket limit (32) reached; finish existing tickets first')
    progress = preparation.start(current, seconds=args.graph_prepare_seconds)
    if progress['status'] not in ('PREPARING', 'CURRENT'):return tool_result(message, progress)
    ticket = uuid.uuid4().hex
    tickets[ticket] = {'message': copy.deepcopy(message), 'identity': graph_key(current), 'preparation_id': progress['preparation_id']}
    return tool_result(message, {**progress, 'status': 'PREPARING', 'ticket': ticket, 'original_call': copy.deepcopy(message.get('params', {})),
                                 'next_action': 'Call graph_wait with this ticket until the actual original result or failure is returned'})


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
            if args.backend == 'gitnexus':
                known = {tool['name'] for tool in message['result'].get('tools', [])}
                message['result'].setdefault('tools', []).extend(copy.deepcopy(tool) for tool in LOCAL_TOOLS if tool['name'] not in known)
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
                instructions += "Graph calls require a matching committed-source/analyzer/export manifest. A cold query returns PREPARING and an exact query ticket: repeatedly call graph_wait(ticket, timeout_seconds<=30) until it returns the actual original query result, or a concrete failure. Do not discard the graph or substitute another analyzer merely because preparation is pending. graph_prepare starts/joins separately bounded preparation; graph_status reports phase/elapsed; graph_cancel addresses only this frontend's exact preparation_id. list_repos is inventory only and never refreshes. Dirty-source requests fail explicitly; use live gopls/AST. Graph calls reuse the immutable generation backend. Equal fingerprints permit documentation-only HEAD reuse. Graph edges are mixed-platform and incomplete."
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
        result["result"]["content"].append({"type": "text", "text": json.dumps({"xray_provenance": {"repo": str(ROOT), "source_head": manifest["head"], "validated_head": after["source"]["head"], "fingerprint": manifest["fingerprint"], "identity": manifest.get('identity'), "coverage": manifest["coverage"]}})})
    if deadline is not None:remaining(deadline,'graph response validation',cancelled=cancelled)
    return result

def handle_request(message, deadline, cancelled):
    """Only the one operation worker may access the generation-owned backend."""
    global catalogue
    method = message.get('method')
    try:
        remaining(deadline,'request admission',cancelled=cancelled)
        control = graph_control(message, deadline, cancelled) if method == 'tools/call' else None
        if control is not None:return control
        if method == 'tools/call' and message.get('params', {}).get('name') == 'list_repos':
            key = graph_session.key or (env['GITNEXUS_HOME'], env['GITNEXUS_STORAGE_PATH'])
            return graph_session.call(key, message, deadline=deadline, cancelled=cancelled)
        if method in ('tools/call','resources/read'):
            current = graph_status(deadline=deadline, cancelled=cancelled)
            if current['status'] != 'CURRENT' and not current['source']['dirty']:
                return cold_query(message, current)
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
            preparation.watchdog()
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
        preparation.close()
        graph_session.close()


def main(argv=None):
    global args, env, command, output, graph_session, startup_deadline, startup_complete, preparation, tickets
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
    parser.add_argument("--graph-prepare-seconds", type=int, default=GRAPH_PREPARE_SECONDS)
    args = parser.parse_args(argv)
    if not 1 <= args.graph_prepare_seconds <= GRAPH_PREPARE_MAX_SECONDS:
        parser.error("--graph-prepare-seconds must be between 1 and " + str(GRAPH_PREPARE_MAX_SECONDS))
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
    preparation = GraphPreparation()
    tickets = {}
    graph_session = PersistentBackend(graph_backend,deadline_factory=True)
    try:serve_graph()
    finally:
        startup_complete.set()
        output.close()


if __name__ == '__main__':
    main()
