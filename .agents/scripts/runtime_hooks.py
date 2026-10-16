"""Trust only the four reviewed Gas City hooks via Codex's native config API."""
import argparse
import json
import hashlib
import re
from pathlib import Path, PurePosixPath
import queue
import subprocess
import threading
import time

# Reviewed GC v1.5.0 command bodies. City is a validated host value, never a
# personal path copied into this bundle. Native identity hashing follows pinned
# Codex config/fingerprint.rs and hooks/engine/discovery.rs (runtime-lock version).
EVENTS={'PreCompact':'pre_compact','SessionStart':'session_start','UserPromptSubmit':'user_prompt_submit'}
PREFIX='export PATH="$HOME/go/bin:$HOME/.local/bin:$PATH" && '


def reviewed_document(city):
    city=str(city)
    if (not re.fullmatch(r'/[A-Za-z0-9_./-]+',city) or '..' in PurePosixPath(city).parts
            or str(PurePosixPath(city))!=city or city.startswith('//') or city=='/'):
        raise ValueError('Hook city requires a canonical shell-safe Linux path')
    command='gc --city '+city+' '
    commands={
        'PreCompact':[command+'handoff --auto --hook-format codex "context cycle"'],
        'SessionStart':['GC_MANAGED_SESSION_HOOK=1 GC_HOOK_EVENT_NAME=SessionStart '+command+'prime --hook --hook-format codex'],
        'UserPromptSubmit':[command+'hook run --timeout 15s --timeout-exit-code 0 -- '+target+' --inject --hook-format codex'
                            for target in ('nudge drain','mail check')],
    }
    return {'hooks':{event:[{'matcher':'startup' if event=='SessionStart' else '',
                            'hooks':[{'type':'command','command':PREFIX+body} for body in bodies]}]
                     for event,bodies in commands.items()}}


def native_fingerprint(value):
    """Pinned Codex version_for_toml canonical JSON identity fingerprint."""
    encoded=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return 'sha256:'+hashlib.sha256(encoded).hexdigest()


def reviewed_hashes(city):
    result={}
    for event,groups in reviewed_document(city)['hooks'].items():
        for index,handler in enumerate(groups[0]['hooks']):
            # Optional None values are omitted during TOML serialization. The
            # native normalized timeout is 600 seconds; only SessionStart keeps
            # its nonempty matcher. All handlers are synchronous.
            identity={'event_name':EVENTS[event],'hooks':[{**handler,'timeout':600,'async':False}]}
            if groups[0]['matcher']:identity['matcher']=groups[0]['matcher']
            result[EVENTS[event]+':0:'+str(index)]=native_fingerprint(identity)
    return result


def prepare_hooks(root,city):
    expected=reviewed_document(city)
    target=root/'.codex/hooks.json'
    if target.resolve()!=target.absolute():
        raise RuntimeError('Hook settings must not alias another path')
    if target.exists():
        if target.is_symlink() or target.stat().st_nlink!=1 or json.loads(target.read_text())!=expected:
            raise RuntimeError('Existing hooks differ from the exact reviewed template; review required')
    else:
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf-8') as handle:
            handle.write(json.dumps(expected,indent=2)+'\n')


def approved_state(root,response,city=None):
    source=str(root/'.codex'/'hooks.json')
    entries=response.get('data',[])
    if len(entries)!=1 or entries[0].get('cwd')!=str(root) or entries[0].get('errors') or entries[0].get('warnings'):
        raise RuntimeError('Cannot establish the exact native hook inventory')
    hooks=entries[0].get('hooks',[]);expected={source+':'+k:v for k,v in reviewed_hashes(city or root).items()}
    if len(hooks)!=len(expected) or {h['key']:h.get('currentHash') for h in hooks}!=expected:
        raise RuntimeError('Generated hooks differ from the reviewed Gas City template; review required')
    if any(h.get('sourcePath')!=source or h.get('source')!='project' or h.get('handlerType')!='command'
           or not h.get('enabled') or h.get('pluginId') for h in hooks):
        raise RuntimeError('Unexpected hook source or handler')
    return {h['key']:{'trusted_hash':h['currentHash']} for h in hooks if h.get('trustStatus')!='trusted'}


def _trust(root,city):
    root=root.resolve()
    prepare_hooks(root,city)
    proc=subprocess.Popen(['/usr/local/bin/codex','-C',str(root),'app-server','--stdio'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8')
    replies=queue.Queue()
    def reader():
        for line in proc.stdout:
            try:replies.put(json.loads(line))
            except ValueError:pass
        replies.put(None)
    threading.Thread(target=reader,daemon=True).start()
    def call(id,method,params):
        proc.stdin.write(json.dumps({'id':id,'method':method,'params':params})+'\n');proc.stdin.flush()
        while True:
            try:reply=replies.get(timeout=20)
            except queue.Empty as error:raise RuntimeError('Native hook configuration timed out') from error
            if reply is None:raise RuntimeError('Native hook configuration process ended')
            if reply.get('id')==id:
                if 'error' in reply:raise RuntimeError(str(reply['error']))
                return reply['result']
    try:
        call(1,'initialize',{'clientInfo':{'name':'mu_runtime_hooks','version':'1'},'capabilities':{'experimentalApi':True}})
        changes=approved_state(root,call(2,'hooks/list',{'cwds':[str(root)]}),city)
        if changes:
            call(3,'config/batchWrite',{'edits':[{'keyPath':'hooks.state','value':changes,'mergeStrategy':'upsert'}],
                                      'reloadUserConfig':True})
        remaining=approved_state(root,call(4,'hooks/list',{'cwds':[str(root)]}),city)
        if remaining:raise RuntimeError('Native hook trust did not persist')
        return {'root':str(root),'reviewed_hooks':4,'newly_trusted':len(changes)}
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()


def trust(root,city=None):
    import fcntl
    path=Path.home()/'.codex/mu-hook-trust.lock'
    with path.open('a+b') as handle:
        deadline=time.monotonic()+30
        while True:
            try:
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic()>=deadline:raise RuntimeError('Hook trust writer is busy; retry the same worker')
                time.sleep(0.05)
        # The OS releases this lock on close or process death.
        return _trust(root,city or root)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--city',type=Path)
    args=parser.parse_args()
    print(json.dumps(trust(args.root,args.city)))
