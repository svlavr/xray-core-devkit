"""Prepare exact advisory inputs and submit independent jobs to native Gas City."""
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone

import workspace
from model_router import select_route, resolve_assignment
from language_policy import WORKER_INSTRUCTIONS

ROOT=workspace.ROOT
STATE=ROOT/'.local/workspace/batches'
FLAGS=getattr(subprocess,'CREATE_NO_WINDOW',0)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False).encode('utf-8')


def save(path,value):
    temp=path.with_suffix('.tmp')
    temp.write_bytes(encoded(value)+b'\n')
    temp.replace(path)


@contextlib.contextmanager
def lock(path):
    with path.open('a+b') as handle:
        handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


def relative(value):
    if not isinstance(value,str) or not value or '\\' in value or ':' in value:
        raise ValueError('Evidence paths must be explicit relative POSIX paths')
    p=PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or str(p)!=value:
        raise ValueError('Evidence path escapes or aliases the source root: '+value)
    if any(x.lower() in {'.git','.env','auth.json','credentials.json'} for x in p.parts):
        raise ValueError('Credentials/Git storage cannot be input evidence')
    if value.casefold().startswith(('.local/workspace/','.codex/config.toml')):
        raise ValueError('Generated host settings cannot be input evidence')
    return value


def check_packet(packet):
    batch=packet.get('batch_id','')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,47}',batch):
        raise ValueError('batch_id needs 3..48 lowercase letters/digits/hyphens')
    jobs=packet.get('jobs',[]);sources=packet.get('sources',{})
    if not 2<=len(jobs)<=23 or not sources:
        raise ValueError('A parallel batch needs 2..23 independent jobs and explicit sources')
    for alias,source in sources.items():
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',alias):
            raise ValueError('Invalid source alias')
        ref=source.get('ref','WORKTREE')
        if ref not in ('WORKTREE','HEAD') and not re.fullmatch(r'[0-9a-f]{40}',ref):
            raise ValueError('Pin source ref to a full commit SHA, HEAD or WORKTREE')
        paths=source.get('paths',[])
        if not paths or len(paths)!=len({relative(p).casefold() for p in paths}):
            raise ValueError('Empty/aliased evidence paths')
    keys=set()
    for job in jobs:
        key=job.get('key','')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,39}',key) or key in keys:
            raise ValueError('Each job needs a unique simple key')
        keys.add(key)
        if job.get('kind') not in ('explore','review','deep') or job.get('depends_on'):
            raise ValueError('Batch jobs are independent read-only advisory tasks')
        title=job.get('title','');body=job.get('body','')
        if not title.strip() or '\n' in title or len(title)>300 or not body.strip():
            raise ValueError('Each job needs a one-line title and scoped body')
        if re.search(r'\b[A-Za-z]:[\\/]|/mnt/[a-z](?:/|\b)',body):
            raise ValueError('Do not give advisers Windows/mounted paths; use source aliases')
        if not job.get('inputs') or any(a not in sources for a in job['inputs']):
            raise ValueError('Every job must select existing source aliases')
        if select_route(job)['action']!='DISPATCH':
            raise ValueError('Resolve missing input/access before submitting the batch')
    return batch


def read_worktree(root,path):
    target=root/path
    if not target.is_file() or target.resolve()!=target.absolute():
        raise ValueError('Missing or linked evidence: '+path)
    for part in [target,*target.parents]:
        if part==root:break
        if part.is_symlink() or getattr(part.lstat(),'st_file_attributes',0)&0x400:
            raise ValueError('Linked/reparse evidence: '+path)
    if target.stat().st_nlink!=1:
        raise ValueError('Hard-linked evidence: '+path)
    return target.read_bytes()


def capture(packet,root=ROOT):
    """Capture worktree bytes or immutable Git blobs, then check for read races."""
    head=workspace.git('rev-parse','HEAD');files={};manifest={};live=[]
    for alias,source in packet['sources'].items():
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',alias) or alias=='tooling':
            raise ValueError('Invalid or reserved source alias: '+str(alias))
        ref=source.get('ref','WORKTREE')
        if ref not in ('WORKTREE','HEAD') and not re.fullmatch(r'[0-9a-f]{40}',ref):
            raise ValueError('Pin source ref to a full SHA, HEAD or WORKTREE')
        sha=head if ref=='HEAD' else ref
        if ref!='WORKTREE':
            sha=workspace.git('rev-parse',sha+'^{commit}')
        for path in source['paths']:
            relative(path)
            if ref=='WORKTREE':
                blob=read_worktree(root,path);live.append((path,blob))
            else:
                entry=workspace.git('ls-tree',sha,'--',path).split()
                if not entry or entry[0] not in ('100644','100755'):
                    raise ValueError('Evidence ref is not a regular Git blob: '+path)
                blob=subprocess.check_output([workspace.git_executable(),'-C',str(root),'show',sha+':'+path],timeout=30,creationflags=FLAGS)
            key=alias+'/'+path
            files[key]=blob
            manifest[key]={'sha256':digest(blob),'bytes':len(blob),'ref':sha}
            if len(files)>512 or len(blob)>8*1024*1024 or sum(len(b) for b in files.values())>64*1024*1024:
                raise ValueError('Evidence exceeds 512 files / 8 MiB per file / 64 MiB total; scope it down')
    if workspace.git('rev-parse','HEAD')!=head or any(read_worktree(root,p)!=b for p,b in live):
        raise RuntimeError('Source changed during capture; retry with stable inputs')
    return head,files,manifest


def verify_copy(directory,manifest):
    for name,entry in manifest.items():
        if digest(read_worktree(directory,name))!=entry['sha256']:
            raise RuntimeError('Snapshot hash mismatch: '+name)


def tooling_inputs(task, root=ROOT):
    """Freeze the selected competency and bounded referenced skill packages."""
    assignment=resolve_assignment(task,root=root)
    if assignment['action']!='DISPATCH':raise ValueError('Resolve missing inputs before freezing launch')
    paths={'.agents/orchestration/models.json','.agents/CODEX_PACK.md'}
    paths.add('go.mod' if (root/'go.mod').is_file() else 'devkit.py')
    for name in ('role_bootstrap.py','role_profiles.py','resource_guard.py','worker_context.py',
                 'go_mcp.py','language_policy.py','runtime_hooks.py'):
        paths.add('.agents/scripts/'+name)
    if assignment.get('role'):
        paths.add(assignment['profile_path'])
    text=assignment.get('developer_instructions','')
    # The profile selects competencies. Main may explicitly add another workflow
    # skill; no task-title/keyword classifier selects a role here.
    skills={folder.name for folder in (root/'.agents/skills').iterdir() if folder.is_dir()
            and re.search(r'(?<![A-Za-z0-9_-])'+re.escape(folder.name)+r'(?![A-Za-z0-9_-])',text)} | set(task.get('skills',[]))
    for skill in skills:
        if not re.fullmatch(r'[a-z][a-z0-9-]*',skill):raise ValueError('Invalid selected skill: '+str(skill))
        folder=root/'.agents/skills'/skill
        if not (folder/'SKILL.md').is_file():raise ValueError('Missing selected skill: '+skill)
        paths.update(p.relative_to(root).as_posix() for p in folder.rglob('*') if p.is_file())
    # Freeze the public authority documents named by the selected profile/skills.
    texts=[text,(root/'.agents/CODEX_PACK.md').read_text(encoding='utf-8')]
    texts.extend(read_worktree(root,path).decode('utf-8') for path in sorted(paths) if path.endswith('.md'))
    documents=set(re.findall(r'(?<![A-Za-z0-9_])docs/[A-Za-z0-9_.-]+\.md','\n'.join(texts)))
    while documents-paths:
        current=documents-paths
        for path in current:
            body=read_worktree(root,path).decode('utf-8')
            documents.update(re.findall(r'(?<![A-Za-z0-9_])docs/[A-Za-z0-9_.-]+\.md',body))
        paths.update(current)
    files={path:read_worktree(root,path) for path in sorted(paths)}
    if assignment.get('role') and digest(files[assignment['profile_path']])!=assignment['profile_sha256']:
        raise RuntimeError('Role changed during capture')
    if any(read_worktree(root,path)!=raw for path,raw in files.items()):
        raise RuntimeError('Tooling changed during capture')
    return assignment,files


def freeze_launches(directory,linux,tasks,head,source_dirs,root=ROOT,*,run_root,run_directory,native_hooks):
    """Materialize hash-bound, job-private inputs before native task creation."""
    from worker_context import adviser_configuration
    if Path(run_directory).resolve().is_relative_to(directory.resolve()):
        raise ValueError('Mutable job state must be outside the frozen input snapshot')
    launches={};all_files={}
    for task in tasks:
        assignment,files=tooling_inputs(task,root)
        key=task['key'];prefix='tooling/'+key;tooling=linux+'/'+prefix
        runtime=Path(run_directory)/key
        if not runtime.is_dir() or not (runtime/'transient').is_dir():
            raise ValueError('Prepare mutable job state as the Linux reader before freezing inputs')
        source=source_dirs(task)
        files['.codex/hooks.json']=native_hooks
        files['.codex/config.toml']=adviser_configuration(tooling,head,source).encode('utf-8')
        files['.local/workspace/context.json']=encoded({'core':tooling,'external_adviser':True,
            'source_base':head,'sources':source,'profile_root':tooling,
            'skills_root':tooling+'/.agents/skills'})+b'\n'
        manifest={path:{'sha256':digest(raw),'bytes':len(raw)} for path,raw in files.items()}
        for path,raw in files.items():
            target=directory/prefix/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            all_files[prefix+'/'+path]=manifest[path]
        # Preserve policy fields; replace host-only authority paths with paths the
        # actual Linux reader can open. Developer bytes are loaded from TOML.
        selected={k:v for k,v in assignment.items() if k not in
            ('profile_toml','developer_instructions','profile_root','context_root','skills_root')}
        selected.update(profile_root=tooling,context_root=tooling+'/.local/workspace',skills_root=tooling+'/.agents/skills')
        launch={'assignment':selected,'tooling_root':tooling,'snapshot_root':linux,
            'run_root':run_root+'/'+key,'source_head':head,'native_hooks_sha256':digest(native_hooks),
            'store_ref':'rig:mu-core' if task['kind']=='implement' else 'city',
            'mode':task.get('kind'),'files':manifest,'body':task['body']+'\n\nRouting/handoff evidence:\n'+
            json.dumps({k:v for k,v in task.items() if k not in ('body','sources')},ensure_ascii=False),
            'escalation':{k:task.get(k) for k in ('previous_model','blocker','discriminator','evidence')}}
        raw=encoded(launch)+b'\n';name=prefix+'/launch.json';(directory/name).write_bytes(raw)
        all_files[name]={'sha256':digest(raw),'bytes':len(raw)}
        launches[key]={'path':linux+'/'+name,'sha256':digest(raw),'assignment':selected}
    if len(all_files)>512 or sum(v['bytes'] for v in all_files.values())>64*1024*1024:
        raise ValueError('Scoped launch tooling exceeds 512 files / 64 MiB; narrow selected skills')
    return launches,all_files


def prepare_run_roots(data,runtime,keys):
    """The selected Linux user owns mutable state; UNC-created directories do not."""
    probe="""import pathlib,sys,tempfile
root=pathlib.Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=False)
for key in sys.argv[2:]:
    assert key and '/' not in key and key not in ('.','..')
    job=root/key;job.mkdir();(job/'transient').mkdir()
    with tempfile.TemporaryFile(dir=job) as output:output.write(b'owned-run-root')
"""
    subprocess.run(['wsl.exe','-d',data['distribution'],'-u',data['user'],'--exec',
        'python3','-c',probe,runtime,*keys],check=True,capture_output=True,timeout=30,creationflags=FLAGS)


def snapshot(data,packet):
    head,files,manifest=capture(packet)
    linux=data['city']+'/.gc/mu-inputs/'+packet['batch_id']+'-'+uuid.uuid4().hex[:12]
    directory=Path('//wsl.localhost')/data['distribution']/linux.lstrip('/')
    runtime=data['city']+'/.gc/mu-runs/'+linux.rsplit('/',1)[1]
    run_directory=Path('//wsl.localhost')/data['distribution']/runtime.lstrip('/')
    city=Path('//wsl.localhost')/data['distribution']/data['city'].lstrip('/')
    # orchestration.main qualified these exact four native hooks before batch or
    # dispatch. Freeze their bytes, never synthesize replacement hook commands.
    native_hooks=read_worktree(city,'.codex/hooks.json')
    prepare_run_roots(data,runtime,[task['key'] for task in packet['jobs']])
    directory.mkdir(parents=True,exist_ok=False)
    for name,blob in files.items():
        target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
    launches,tooling=freeze_launches(directory,linux,packet['jobs'],head,
        lambda task:[linux+'/'+a for a in task['inputs']],run_root=runtime,run_directory=run_directory,
        native_hooks=native_hooks)
    if read_worktree(city,'.codex/hooks.json')!=native_hooks:
        raise RuntimeError('Native city hooks changed during snapshot capture')
    manifest.update(tooling)
    if len(manifest)>512 or sum(v['bytes'] for v in manifest.values())>64*1024*1024:
        raise ValueError('Combined source/tooling snapshot exceeds 512 files / 64 MiB; scope it down')
    verify_copy(directory,manifest)
    # Windows verifies the written bytes; Linux proves the actual reader namespace.
    (directory/'manifest.json').write_bytes(encoded({'source_head':head,'files':manifest})+b'\n')
    probe="""import json,hashlib,pathlib,sys,tempfile
p=pathlib.Path(sys.argv[1]);m=json.loads((p/'manifest.json').read_text())
assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==v['sha256'] for n,v in m['files'].items())
for name in m['files']:
    if not name.startswith('tooling/') or not name.endswith('/launch.json'):continue
    launch=json.loads((p/name).read_text());runtime=pathlib.Path(launch['run_root'])
    assert runtime.is_dir() and not runtime.resolve().is_relative_to(p.resolve())
    with tempfile.TemporaryFile(dir=runtime) as output:output.write(b'prepared-run-root')
print(len(m['files']))
"""
    subprocess.run(['wsl.exe','-d',data['distribution'],'-u',data['user'],'--exec','python3','-c',probe,linux],
        check=True,capture_output=True,timeout=30,creationflags=FLAGS)
    return {'linux':linux,'source_head':head,'files':manifest,'launches':launches,
            'manifest_sha256':digest((directory/'manifest.json').read_bytes())}


class Native:
    def __init__(self,data,command,store_ref='city'):
        if store_ref not in ('city','rig:mu-core'):raise ValueError('Unknown Core native bead store')
        self.data=data;self.command=command;self.store_ref=store_ref
    def scoped(self,store_ref):return Native(self.data,self.command,store_ref)
    def run(self,args,body=None):
        if self.store_ref=='rig:mu-core' and args[:1]==['bd']:
            args=['bd','--rig','mu-core',*args[1:]]
        result=subprocess.run(self.command(self.data,args),input=body,capture_output=True,timeout=60,creationflags=FLAGS)
        if result.returncode:
            raise RuntimeError(result.stderr.decode('utf-8',errors='replace') or result.stdout.decode('utf-8',errors='replace'))
        if result.stderr:sys.stderr.write(result.stderr.decode('utf-8',errors='replace'))
        return result.stdout
    def show(self,id):
        try:return json.loads(self.run(['bd','show',id,'--json']))[0]
        except RuntimeError as error:
            if re.search(r'not found|no issue found',str(error),re.I):return None
            raise


def planned_jobs(packet,evidence):
    jobs=[]
    for task in packet['jobs']:
        binding=evidence.get('launches',{}).get(task['key'])
        route=binding['assignment'] if binding else select_route(task)
        store_ref='rig:mu-core' if task['kind']=='implement' else 'city'
        scope=('Owned implementation job '+packet['batch_id']+'. Honor only the dispatched write set in your prepared worker checkout. No publication, delegation or messages. '
               if task['kind']=='implement' else
               'Independent READ-ONLY job in parallel batch '+packet['batch_id']+'. No source edits, Git writes, delegation or messages. ')
        body=(WORKER_INSTRUCTIONS+'\n\n'+scope+
              'Other agents work on different questions; inspect only your inputs and return findings, not another full audit.\n'
              'Evidence is already copied and verified inside this Linux environment. Do not request Windows mounts.\n'
              'Snapshot root: '+evidence['linux']+'\nManifest: '+evidence['linux']+'/manifest.json\n'
              'Source HEAD: '+evidence['source_head']+'; WORKTREE files are pinned by individual hashes, not HEAD.\n'
              'Your source directories: '+', '.join(evidence['linux']+'/'+a for a in task['inputs'])+'\n\n'+task['body']+
              '\n\nRecord a comment whose first line is exactly one of: status: DONE; status: NEEDS_CONTEXT; status: UNRESOLVED_TECHNICAL. '
              'On subsequent lines give evidence/findings/limits. '
              'Close only your task after saving the result and drain. Never fabricate success for unavailable evidence.')
        title='['+packet['batch_id']+'/'+task['key']+'] '+task['title']
        hash=digest(encoded({'title':title,'body':body,'route':route,'launch':binding}))
        metadata={'mu.task_hash':hash,'mu.store_ref':store_ref}
        if binding:
            metadata.update({'mu.launch_path':binding['path'],'mu.launch_sha256':binding['sha256'],
                'mu.role':route.get('role','legacy'),'mu.profile_sha256':route.get('profile_sha256',''),
                'mu.context_root':route['context_root'],'mu.skills_root':route['skills_root']})
        elif route.get('role'):
            raise ValueError('Selected role has no frozen launch inputs')
        prefix='mux-b-' if store_ref=='rig:mu-core' else 'mc-b-'
        jobs.append({'key':task['key'],'id':prefix+digest((packet['batch_id']+'/'+task['key']).encode())[:20],
                     'store_ref':store_ref,
                     'title':title,'body':body,'hash':hash,'route':route,'metadata':metadata,'phase':'planned'})
    return jobs


def matches(actual,job):
    if actual is None:raise RuntimeError('Native task disappeared: '+job['id'])
    if (actual.get('id')!=job['id'] or actual.get('title')!=job['title'] or actual.get('description')!=job['body']
            or actual.get('metadata',{}).get('mu.task_hash')!=job['hash']):
        raise RuntimeError('Existing native task differs from this batch: '+job['id'])
    if any(actual.get('metadata',{}).get(key)!=value for key,value in job.get('metadata',{}).items()):
        raise RuntimeError('Existing native task launch metadata differs: '+job['id'])
    route=actual.get('metadata',{}).get('gc.routed_to')
    if route and route!=job['route']['target']:
        raise RuntimeError('Existing task is routed to another pool: '+job['id'])
    if actual.get('assignee') and not route:
        raise RuntimeError('Task has an unrelated assignee: '+job['id'])


def enqueue(state,native,persist):
    # Stage all native beads, then route all ready jobs before any monitoring.
    for job in state['jobs']:
        store_ref=job.get('store_ref','city')
        if job['route']['target'].startswith('mu-core/')!=(store_ref=='rig:mu-core'):
            raise RuntimeError('Native task store differs from target rig; preserve/reconcile old admission: '+job['id'])
        scoped=native.scoped(store_ref)
        actual=scoped.show(job['id'])
        if actual is None:
            job['phase']='creating';persist()
            scoped.run(['bd','create',job['title'],'--id',job['id'],'--type','task','--status','open',
                '--labels','mu-batch:'+state['batch_id'],'--metadata',json.dumps(job.get('metadata',{'mu.task_hash':job['hash']})),
                '--body-file','-','--silent'],job['body'].encode('utf-8'))
            actual=scoped.show(job['id'])
        if actual is None:raise RuntimeError('Create outcome unknown: '+job['id'])
        matches(actual,job);job['phase']='created';persist()
    errors=[]
    for job in state['jobs']:
        try:
            scoped=native.scoped(job.get('store_ref','city'))
            actual=scoped.show(job['id']);matches(actual,job)
            if actual['status']=='closed':job['phase']='closed'
            elif actual.get('metadata',{}).get('gc.routed_to')==job['route']['target'] and actual.get('assignee'):
                owner=native.show(actual['assignee'])
                if (not owner or owner.get('id')!=actual['assignee'] or owner.get('issue_type')!='session'
                        or owner.get('status')=='closed' or owner.get('metadata',{}).get('state')=='closed'
                        or owner.get('metadata',{}).get('template')!=job['route']['target']):
                    raise RuntimeError('Claim belongs to an unverified pool session; reconcile '+job['id'])
                job['phase']='claimed'
            else:
                if actual['status']!='open' or actual.get('assignee'):
                    raise RuntimeError('Task is not unassigned ready work; reconcile '+job['id'])
                recovery=actual.get('metadata',{}).get('gc.routed_to')==job['route']['target']
                job['phase']='routing';persist()
                scoped.run(['sling',job['route']['target'],job['id'],'--no-formula','--no-convoy',
                            *(['--nudge'] if recovery else []),'--json'])
                confirmed=scoped.show(job['id']);matches(confirmed,job)
                if confirmed.get('metadata',{}).get('gc.routed_to')!=job['route']['target']:
                    raise RuntimeError('Native routing postcondition missing: '+job['id'])
                job['phase']='routed'
            job.pop('error',None)
        except (RuntimeError,subprocess.SubprocessError) as error:
            job['error']=str(error);errors.append(job['id'])
        persist()
    if errors:raise RuntimeError('Partial batch; resume the same packet/IDs after inspection: '+', '.join(errors))


def namespace(data):
    return {**{k:data[k] for k in ('distribution','user','city')},'integration_root':str(ROOT)}


def check_namespace(state,data):
    if state.get('namespace')!=namespace(data):raise RuntimeError('Batch belongs to a different native namespace or integration root')


def run_batch(data,path,command):
    packet=json.loads(Path(path).read_text(encoding='utf-8'));batch=check_packet(packet)
    workspace.repository_guard();STATE.mkdir(parents=True,exist_ok=True)
    record=STATE/(batch+'.json')
    with lock(STATE/(batch+'.lock')):
        if record.exists():
            state=json.loads(record.read_text(encoding='utf-8'))
            check_namespace(state,data)
            if state['packet_hash']!=digest(encoded(packet)):raise ValueError('Batch ID already owns a different packet')
            directory=Path('//wsl.localhost')/data['distribution']/state['evidence']['linux'].lstrip('/')
            verify_copy(directory,state['evidence']['files'])
            if digest((directory/'manifest.json').read_bytes())!=state['evidence']['manifest_sha256']:
                raise RuntimeError('Snapshot manifest changed')
        else:
            evidence=snapshot(data,packet)
            state={'batch_id':batch,'namespace':namespace(data),'packet_hash':digest(encoded(packet)),'evidence':evidence,
                'created_at':datetime.now(timezone.utc).isoformat(),'jobs':planned_jobs(packet,evidence)}
            save(record,state)
        enqueue(state,Native(data,command),lambda:save(record,state))
        return {'batch_id':batch,'snapshot':state['evidence']['linux'],'source_head':state['evidence']['source_head'],
                'jobs':[{k:j[k] for k in ('key','id','route','phase')} for j in state['jobs']],
                'next':'orchestration.py batch-status '+batch}


def batch_status(data,batch,command):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,47}',batch):raise ValueError('Invalid batch ID')
    state=json.loads((STATE/(batch+'.json')).read_text(encoding='utf-8'));native=Native(data,command)
    check_namespace(state,data)
    directory=Path('//wsl.localhost')/data['distribution']/state['evidence']['linux'].lstrip('/')
    verify_copy(directory,state['evidence']['files'])
    if digest((directory/'manifest.json').read_bytes())!=state['evidence']['manifest_sha256']:
        raise RuntimeError('Snapshot manifest changed; advisory evidence must be requalified')
    rows=[]
    for job in state['jobs']:
        scoped=native.scoped(job.get('store_ref','city'))
        item=scoped.show(job['id'])
        if item is None:rows.append({'key':job['key'],'id':job['id'],'status':'unknown'});continue
        matches(item,job)
        comments=json.loads(scoped.run(['bd','comments',job['id'],'--json'])) if item['status']=='closed' or item.get('comment_count') else []
        outcomes=[m.group(1) for c in comments if (m:=re.search(r'^status:\s*(DONE|NEEDS_CONTEXT|UNRESOLVED_TECHNICAL)\s*$',c['text'],re.M))]
        rows.append({'key':job['key'],'id':job['id'],'model':job['route']['model'],'effort':job['route']['effort'],
            'role':job['route'].get('role','legacy'),'profile_sha256':job['route'].get('profile_sha256'),
            'status':item['status'],'assignee':item.get('assignee'),'started_at':item.get('started_at'),
            'closed_at':item.get('closed_at'),'result':outcomes[-1] if outcomes else None,'comments':comments})
    sessions=json.loads(native.run(['session','list','--json']))
    return {'batch_id':batch,'jobs':rows,'sessions':sessions,'all_done':all(j['status']=='closed' and j.get('result')=='DONE' for j in rows)}
