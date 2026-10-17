"""Host entrypoint for the installed Gas City runtime; no replacement scheduler."""
import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import shutil
import re
import tomllib
import hashlib
import uuid
import inspect


def set_field(text, section, key, value):
    """Update one managed scalar while preserving rigs and unrelated settings."""
    header = '[' + section + ']'
    match = re.search(r'^' + re.escape(header) + r'\s*$', text, re.M)
    line = key + ' = ' + json.dumps(value)
    if not match:
        return text.rstrip() + '\n\n' + header + '\n' + line + '\n'
    start = match.end()
    following = re.search(r'^\[', text[start:], re.M)
    end = start + following.start() if following else len(text)
    block = text[start:end]
    pattern = r'^' + re.escape(key) + r'\s*=.*$'
    if re.search(pattern, block, re.M):
        block = re.sub(pattern, lambda _: line, block, count=1, flags=re.M)
    else:
        block = '\n' + line + '\n' + block
    return text[:start] + block + text[end:]


def set_agent_field(text, name, rig, key, value):
    matches=[]
    for match in re.finditer(r'^\[\[patches\.agent\]\][ \t]*$',text,re.M):
        start=match.end()
        following=re.search(r'^\[',text[start:],re.M)
        end=start+following.start() if following else len(text)
        block=text[match.start():end]
        item=tomllib.loads(block)['patches']['agent'][0]
        if item.get('name')==name and item.get('rig','')==rig:
            matches.append((start,end))
    if len(matches)>1:
        raise RuntimeError('Duplicate managed agent patch: '+name+'/'+rig)
    line=key+' = '+json.dumps(value)
    if not matches:
        return text.rstrip()+'\n\n[[patches.agent]]\nname = '+json.dumps(name)+'\n'+(
            'rig = '+json.dumps(rig)+'\n' if rig else '')+line+'\n'
    start,end=matches[0];block=text[start:end]
    pattern=r'^'+re.escape(key)+r'\s*=.*$'
    if re.search(pattern,block,re.M):
        block=re.sub(pattern,lambda _:line,block,count=1,flags=re.M)
    else:
        block='\n'+line+'\n'+block
    return text[:start]+block+text[end:]

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ROOT / '.local/workspace/orchestration.json'
FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
KEEPALIVE = ROOT / '.local/workspace/orchestration-keepalive.json'


def owned_keepalive():
    if not KEEPALIVE.exists():
        return None
    record = json.loads(KEEPALIVE.read_text(encoding='utf-8'))
    pid = int(record['pid'])
    query = f'Get-CimInstance Win32_Process -Filter "ProcessId = {pid}" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress'
    output = subprocess.check_output(['powershell.exe', '-NoProfile', '-NonInteractive',
        '-Command', query], text=True, encoding='utf-8', creationflags=FLAGS, timeout=15).strip()
    if not output:
        return None
    process = json.loads(output)
    if process.get('CommandLine') != record['command_line']:
        raise RuntimeError('Keepalive PID was reused; inspect the receipt before starting/stopping')
    return pid


def ensure_keepalive(data):
    if owned_keepalive():
        return
    cmd = [shutil.which('wsl.exe') or 'wsl.exe', '-d', data['distribution'],
           '-u', data['user'], '--exec', 'sleep', 'infinity']
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, creationflags=FLAGS | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
    KEEPALIVE.write_text(json.dumps({'pid': proc.pid, 'command_line': subprocess.list2cmdline(cmd)})+'\n',encoding='utf-8')


def stop_keepalive():
    pid = owned_keepalive()
    if pid:
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
            f'Stop-Process -Id {pid} -ErrorAction Stop'], check=True,
            creationflags=FLAGS, timeout=15)
    KEEPALIVE.unlink(missing_ok=True)


def ensure_tmux(data):
    """Keep the owned city socket observable even with zero LLM sessions."""
    directory=Path('//wsl.localhost')/data['distribution']/data['city'].lstrip('/')
    name=tomllib.loads((directory/'city.toml').read_text(encoding='utf-8'))['workspace'].get('name',directory.name)
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',name):
        raise RuntimeError('Unexpected city tmux socket name')
    config=directory/'.gc/mu-idle-tmux.conf'
    config.write_text('set-option -s exit-empty off\n',encoding='utf-8',newline='\n')
    prefix=['wsl.exe','-d',data['distribution'],'-u',data['user'],'--exec','tmux','-L',name]
    subprocess.run([*prefix,'-f',data['city']+'/.gc/mu-idle-tmux.conf','start-server'],
        check=True,capture_output=True,timeout=15,creationflags=FLAGS)
    subprocess.run([*prefix,'set-option','-s','exit-empty','off'],
        check=True,capture_output=True,timeout=15,creationflags=FLAGS)


def validate_context(data):
    """Reject accidental connection to another checkout or Windows-mounted runtime."""
    if Path(data.get('integration_root', '')).resolve() != ROOT:
        raise RuntimeError('Orchestration context belongs to another integration checkout')
    for key in ('distribution', 'user'):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', data.get(key, '')):
            raise ValueError('Invalid orchestration '+key)
    if data['user'] == 'root':
        raise ValueError('Agents require a dedicated unprivileged Linux user')
    for key in ('city', 'rig_root', 'queue_origin', 'worktree_base', 'analysis_tools'):
        value=data.get(key, '')
        path=PurePosixPath(value)
        if (not path.is_absolute() or value.startswith('//') or str(path)!=value or '..' in path.parts
                or value=='/' or re.search(r"[\s'\\:;`$]", value)
                or value=='/mnt' or value.startswith('/mnt/')):
            raise ValueError('Use a canonical Linux filesystem path for '+key)
    locations=[PurePosixPath(data[k]) for k in ('city','rig_root','queue_origin','worktree_base','analysis_tools')]
    for index,left in enumerate(locations):
        for right in locations[index+1:]:
            # Rigs may conventionally live below the city; other stores must be disjoint.
            if left == right or ((left.is_relative_to(right) or right.is_relative_to(left))
                    and {left,right} != {PurePosixPath(data['city']),PurePosixPath(data['rig_root'])}):
                raise ValueError('Runtime stores/worktrees/tools must have separate locations')
    proxy=data.get('http_proxy','')
    if proxy:
        from urllib.parse import urlsplit
        parsed=urlsplit(proxy)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Proxy must be an HTTP(S) endpoint without embedded credentials')
    return data


def context():
    return validate_context(json.loads(CONTEXT.read_text(encoding='utf-8')))


def init_context(path):
    """Install only an explicitly edited host example; never overwrite a connection."""
    from workspace import host_target
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    data['integration_root']=str(ROOT)
    validate_context(data)
    target=host_target('.local/workspace/orchestration.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as handle:
        handle.write(json.dumps(data,indent=2)+'\n')
    return {'context':str(target),'connected':False,'next':'Follow docs/ORCHESTRATION.md before configure'}


def command(data, args):
    return ['wsl.exe', '-d', data['distribution'], '-u', data['user'],
            '--cd', data['city'], '--exec', '/usr/local/bin/gc', '--city', data['city'], *args]


def boundary_report(config_text, mounts, uid, vm_interop_registered):
    """WSL2 binfmt registration is VM-wide, not a per-distro access switch."""
    import configparser
    c=configparser.ConfigParser();c.read_string(config_text)
    checks={'unprivileged_user':uid!=0,
        'automount_disabled':not c.getboolean('automount','enabled',fallback=True),
        'interop_disabled':not c.getboolean('interop','enabled',fallback=True),
        'windows_path_disabled':not c.getboolean('interop','appendWindowsPath',fallback=True),
        'no_windows_drive_mounts':'aname=drvfs' not in mounts and ' - drvfs ' not in mounts}
    return {'allowed':all(checks.values()),'checks':checks,'uid':uid,
            'vm_interop_registered':vm_interop_registered}


def verify_boundary(data):
    probe = "import os,json\n"+inspect.getsource(boundary_report)+"""
from pathlib import Path
result=boundary_report(Path('/etc/wsl.conf').read_text(),Path('/proc/self/mountinfo').read_text(),
    os.geteuid(),Path('/proc/sys/fs/binfmt_misc/WSLInterop').exists())
print(json.dumps(result))
raise SystemExit(0 if result['allowed'] else 1)
"""
    checked = subprocess.run(['wsl.exe','-d',data['distribution'],'-u',data['user'],
        '--exec','python3','-c',probe], capture_output=True, text=True, encoding='utf-8',
        creationflags=FLAGS, timeout=20)
    if checked.returncode:
        raise RuntimeError('WSL boundary check failed: '+(checked.stdout.strip() or checked.stderr.strip()))
    result=json.loads(checked.stdout)
    if result.get('allowed') is not True:raise RuntimeError('WSL boundary probe did not confirm the configured boundary')
    return result


def configure(data):
    from context_policy import settings
    template = tomllib.loads((ROOT / '.agents/orchestration/city.toml').read_text())
    runtime=runtime_tools(data)
    record=CONTEXT.parent/'legacy-jobs.json'
    legacy=' --legacy-record '+runtime+'/legacy-jobs.json --legacy-sha '+hashlib.sha256(record.read_bytes()).hexdigest()
    template['providers']['codex']['command']=runtime+'/role_bootstrap.py'+legacy
    template['providers']['codex']['resume_command']=runtime+'/role_bootstrap.py'+legacy+' resume {{.SessionKey}}'
    catalog=Path('//wsl.localhost')/data['distribution']/'home'/data['user']/'.codex/models_cache.json'
    context_options=settings(json.loads(catalog.read_text(encoding='utf-8')))
    for key,value in context_options.items():
        template['providers']['codex']['args_append']+=['-c',key+'='+json.dumps(value)]
    target = Path('//wsl.localhost') / data['distribution'] / data['city'].lstrip('/') / 'city.toml'
    original = target.read_text(encoding='utf-8')
    text = original
    managed = {
        'workspace': template['workspace'],
        'daemon': template['daemon'],
        'providers.codex': {k: v for k, v in template['providers']['codex'].items() if not isinstance(v, dict)},
        'providers.codex.option_defaults': template['providers']['codex']['option_defaults'],
        'providers.codex.env': {'HTTP_PROXY': data.get('http_proxy',''), 'HTTPS_PROXY': data.get('http_proxy',''),
                                'NO_PROXY': 'localhost,127.0.0.1,::1'},
    }
    managed['defaults.rig.imports.gc']=template['defaults']['rig']['imports']['gc']
    for section, fields in managed.items():
        for key, value in fields.items():
            text = set_field(text, section, key, value)
    for patch in template.get('patches',{}).get('agent',[]):
        for key,value in patch.items():
            if key not in ('name','rig'):
                if key=='pre_start':value=[entry.replace('/usr/local/lib/mu-runtime',runtime) for entry in value]
                text=set_agent_field(text,patch['name'],patch.get('rig',''),key,value)
    parsed = tomllib.loads(text)
    if parsed.get('rigs') != tomllib.loads(original).get('rigs'):
        raise RuntimeError('Configuration changed registered rigs')
    if text != original:
        (CONTEXT.parent / 'city-before-configure.toml').write_text(original, encoding='utf-8')
        target.write_text(text, encoding='utf-8', newline='\n')
    print(json.dumps({'configured': str(target), 'changed': text != original,
                      'worker_capacity': 23, 'registered_rigs_preserved': True}))


def legacy_jobs(data):
    """Capture existing unbound native identities once, before switching providers."""
    from agent_batch import encoded,namespace,check_namespace
    import shlex
    path=CONTEXT.parent/'legacy-jobs.json'
    config=Path('//wsl.localhost')/data['distribution']/data['city'].lstrip('/')/'city.toml'
    current=tomllib.loads(config.read_text(encoding='utf-8'))
    provider=shlex.split(current.get('providers',{}).get('codex',{}).get('command',''))
    if '--legacy-record' in provider:
        # The switch already happened. Never widen the retained identities now.
        if '--legacy-sha' not in provider:raise RuntimeError('Installed legacy binding has no exact hash')
        expected=provider[provider.index('--legacy-sha')+1]
        raw=path.read_bytes();saved=json.loads(raw);check_namespace(saved,data)
        if hashlib.sha256(raw).hexdigest()!=expected:
            raise RuntimeError('Retained legacy identities differ from the installed provider binding')
        return raw
    stores=['city']
    if any(r.get('name')=='mu-core' for r in current.get('rigs',[])):
        stores.append('rig:mu-core')
    sessions=json.loads(subprocess.check_output(command(data,['session','list','--state','all','--json']),
        text=True,encoding='utf-8',stderr=subprocess.PIPE,creationflags=FLAGS,timeout=60))
    saved={'namespace':namespace(data),'sessions':[item['id'] for item in sessions['sessions']
        if 'role_bootstrap.py' not in item.get('command','')
        and 'role_bootstrap.py' not in item.get('resume_command','')],
        'tasks':{store:[] for store in stores}}
    for store in stores:
        args=['bd',*(['--rig','mu-core'] if store=='rig:mu-core' else []),
              'list','--all','--json','--limit','10000']
        output=subprocess.check_output(command(data,args),text=True,encoding='utf-8',
            stderr=subprocess.PIPE,creationflags=FLAGS,timeout=60)
        entries=json.loads(output)
        if len(entries)>=10000:raise RuntimeError('Paginate existing native identities before upgrading provider')
        for item in entries:
            meta=item.get('metadata',{})
            if item.get('issue_type')=='session':continue
            if not any(key.startswith('mu.launch_') or key in ('mu.role','mu.profile_sha256') for key in meta):
                saved['tasks'][store].append(item['id'])
    raw=encoded(saved)+b'\n'
    # A failed deployment before the provider switch leaves the original path
    # active. Refresh that pre-switch capture on retry, then retain it once bound.
    temporary=path.with_suffix('.tmp');temporary.write_bytes(raw);temporary.replace(path)
    return raw


def deploy_tools(data):
    legacy_jobs(data)
    names=['legacy-jobs.json','go_mcp.py','resource_guard.py','worker_context.py','language_policy.py','provision_worker.py','runtime_hooks.py',
           'role_bootstrap.py','role_profiles.py']
    prefix=Path('//wsl.localhost')/data['distribution']
    incoming='/home/'+data['user']+'/bootstrap'
    destination=prefix/incoming.lstrip('/')
    destination.mkdir(parents=True,exist_ok=True)
    hashes={}
    for name in names:
        source=CONTEXT.parent/name if name=='legacy-jobs.json' else ROOT/'.agents/scripts'/name
        shutil.copyfile(source,destination/name)
        hashes[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    runtime='/usr/local/lib/mu-runtime/bundles/'+hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    subprocess.run(['wsl.exe','-d',data['distribution'],'-u','root','--exec',
        'install','-d','-m','755',runtime],check=True,timeout=15,
        creationflags=FLAGS)
    subprocess.run(['wsl.exe','-d',data['distribution'],'-u','root','--exec',
        'install','-m','644',*[incoming+'/'+n for n in names],runtime+'/'],
        check=True,timeout=15,creationflags=FLAGS)
    subprocess.run(['wsl.exe','-d',data['distribution'],'-u','root','--exec',
        'chmod','755',runtime+'/role_bootstrap.py'],check=True,timeout=15,
        creationflags=FLAGS)
    installed=prefix/runtime.lstrip('/')
    if any(hashlib.sha256((installed/name).read_bytes()).hexdigest()!=hashes[name] for name in names):
        raise RuntimeError('Deployed worker helper bytes differ from the verified input set')
    (CONTEXT.parent/'deployed-worker-tools.json').write_text(json.dumps({'runtime':runtime,'files':hashes},indent=2)+'\n',encoding='utf-8')


def configure_trusted_projects(path, roots):
    """Initialize only missing dedicated-user config; preserve unrelated settings."""
    if path.resolve()!=path.absolute() or (path.exists() and path.stat().st_nlink!=1):
        raise RuntimeError('Codex user config must not alias another path')
    try:
        original=path.read_text(encoding='utf-8')
        exists=True
    except FileNotFoundError:
        original='';exists=False
    tomllib.loads(original)
    text=original
    for root in roots:
        text=set_field(text,'projects.'+json.dumps(root,ensure_ascii=False),'trust_level','trusted')
    tomllib.loads(text)
    if text!=original:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w' if exists else 'x',encoding='utf-8',newline='\n') as handle:
            handle.write(text)


def runtime_tools(data):
    receipt=json.loads((CONTEXT.parent/'deployed-worker-tools.json').read_text(encoding='utf-8'))
    runtime=receipt['runtime']
    if not re.fullmatch(r'/usr/local/lib/mu-runtime/bundles/[0-9a-f]{64}',runtime):
        raise RuntimeError('Unexpected immutable runtime tooling path; configure current tools')
    prefix=Path('//wsl.localhost')/data['distribution']/runtime.lstrip('/')
    if any(hashlib.sha256((prefix/name).read_bytes()).hexdigest()!=sha for name,sha in receipt['files'].items()):
        raise RuntimeError('Installed immutable runtime tooling changed')
    return runtime



def configure_advisers(data):
    from language_policy import WORKER_INSTRUCTIONS
    policy=json.loads((ROOT/'.agents/orchestration/models.json').read_text())
    output=subprocess.check_output(command(data,['config','show']),text=True, encoding='utf-8',
        stderr=subprocess.PIPE,creationflags=FLAGS,timeout=30)
    resolved=tomllib.loads(output)
    base=next(a['prompt_template'] for a in resolved['agent'] if a['name']=='codex' and not a.get('dir'))
    prefix=Path('//wsl.localhost')/data['distribution']
    native=(prefix/base.lstrip('/')).read_text(encoding='utf-8')
    overlay=WORKER_INSTRUCTIONS+'\n\n'+(ROOT/'.agents/orchestration/adviser-policy.md').read_text()
    for route in ('explore','review','deep'):
        spec=policy[route]
        directory=prefix/data['city'].lstrip('/')/'agents'/spec['target']
        directory.mkdir(parents=True,exist_ok=True)
        (directory/'prompt.template.md').write_text(overlay+'\n\n'+native,encoding='utf-8',newline='\n')
        # Native GC overlays run before our bootstrap. Give each concrete slot
        # its own mutable cwd; never let that overlay rewrite canonical city hooks
        # or a frozen task snapshot. GC creates these paths as the Linux user.
        config='provider = "codex"\nwork_dir = ".gc/mu-advisers/{{.AgentBase}}"\nmax_active_sessions = '+str(spec['max_active'])+'\n'
        config+='[option_defaults]\nmodel = '+json.dumps(spec['model'])+'\neffort = '+json.dumps(spec['effort'])+'\n'
        (directory/'agent.toml').write_text(config,encoding='utf-8',newline='\n')
    user_config=prefix/'home'/data['user']/'.codex/config.toml'
    configure_trusted_projects(user_config,[data['rig_root'],data['city']])


def check_models(data):
    from model_router import validate_models
    output=subprocess.check_output(command(data,['config','show']),text=True, encoding='utf-8',
        stderr=subprocess.PIPE,creationflags=FLAGS,timeout=30)
    validate_models(tomllib.loads(output))


def trust_city_hooks(data):
    checked=subprocess.run(['wsl.exe','-d',data['distribution'],'-u',data['user'],'--exec','python3',
        runtime_tools(data)+'/runtime_hooks.py','--root',data['city']],capture_output=True,
        timeout=60,creationflags=FLAGS)
    if checked.returncode:
        raise RuntimeError('Reviewed hook preparation failed: '+checked.stderr.decode('utf-8',errors='replace').strip())


def dispatch(data, path):
    from model_router import resolve_assignment
    from agent_batch import (snapshot,planned_jobs,enqueue,Native,STATE,save,lock,digest,encoded,
        namespace,check_namespace,verify_copy)
    task=json.loads(Path(path).read_text(encoding='utf-8'))
    route=resolve_assignment(task,root=ROOT)
    if route['action']!='DISPATCH':
        print(json.dumps(route));return 0
    title=task.get('title','').strip();body=task.get('body','').strip()
    if re.search(r'\b[A-Za-z]:[\\/]|/mnt/[a-z](?:/|\b)',body):
        raise ValueError('External agents cannot read Windows paths; use batch sources for verified input delivery')
    if not title or '\n' in title or len(title)>450 or not body:
        raise ValueError('A task packet needs a one-line title and scoped body')
    if task['kind']=='implement':
        missing=[key for key in ('base','write_set','acceptance','validation','stop_conditions') if not task.get(key)]
        if missing:raise ValueError('Implementation packet requires '+', '.join(missing))
        from agent_batch import relative
        if not isinstance(task['write_set'],list):raise ValueError('Implementation write_set must name exact relative paths')
        for owned in task['write_set']:
            relative(owned)
            if owned=='.' or any(char in owned for char in '*?['):raise ValueError('Implementation write_set must name exact relative paths')
    identity='single-'+digest(encoded(task))[:24]
    packet={'batch_id':identity,'sources':task.get('sources',{}),
        'jobs':[{**task,'key':'task','inputs':list(task.get('sources',{}))}]}
    # Same immutable native IDs and reconciliation as batches. A timed-out create
    # or sling is never retried under another identity.
    STATE.mkdir(parents=True,exist_ok=True)
    record=STATE/(identity+'.json')
    with lock(STATE/(identity+'.lock')):
        if record.exists():
            state=json.loads(record.read_text(encoding='utf-8'));check_namespace(state,data)
            if state['packet_hash']!=digest(encoded(packet)):raise ValueError('Dispatch identity owns another packet')
            directory=Path('//wsl.localhost')/data['distribution']/state['evidence']['linux'].lstrip('/')
            verify_copy(directory,state['evidence']['files'])
            if digest((directory/'manifest.json').read_bytes())!=state['evidence']['manifest_sha256']:
                raise RuntimeError('Dispatch snapshot manifest changed')
        else:
            evidence=snapshot(data,packet)
            if task['kind']=='implement':
                active=Path('//wsl.localhost')/data['distribution']/data['rig_root'].lstrip('/')/'.local/workspace/dispatch.json'
                wave=json.loads(active.read_text(encoding='utf-8'))
                if task['base']!=wave['source_head'] or evidence['source_head']!=wave['source_head']:
                    raise RuntimeError('Implementation base differs from prepared worker source; prepare current idle wave')
            state={'batch_id':identity,'namespace':namespace(data),'packet_hash':digest(encoded(packet)),
                   'evidence':evidence,'jobs':planned_jobs(packet,evidence)}
            save(record,state)
        enqueue(state,Native(data,command),lambda:save(record,state))
    print(json.dumps({'routing':state['jobs'][0]['route'],'dispatch':
        {k:state['jobs'][0][k] for k in ('id','phase','metadata')},'receipt':str(record)}))
    return 0


def reusable_wave(receipts, jobs, head, active_manifest):
    """Only the active, open, successfully prepared wave can be reused."""
    for job in jobs:
        receipt=receipts/(job['id']+'.json')
        if job['status']=='closed' or not receipt.is_file():
            continue
        saved=json.loads(receipt.read_text(encoding='utf-8'))
        if saved['source_head']==head:
            if not active_manifest.is_file() or json.loads(active_manifest.read_text(encoding='utf-8'))!=saved:
                raise RuntimeError('Open prepared wave differs from active dispatch; reconcile before preparing')
            return saved
    return None


def reload_prepared_city(linux, city):
    """Reload live GC, deferring only a positively observed stopped controller.

    GC v1.5 cmd_citystatus.go resolves controller identity locally even when
    agent rows are cached. A live supervisor with unknown city state reports
    status='unknown'; it must not be mistaken for a stopped cold bootstrap.
    """
    status=json.loads(linux(['/usr/local/bin/gc','--city',city,'status','--json']))
    controller=status.get('controller',{})
    if (status.get('schema_version')!='1' or status.get('ok') is not True
            or status.get('city_path')!=city or status.get('partial')
            or status.get('partial_errors') or not isinstance(controller,dict)
            or not isinstance(controller.get('running'),bool)):
        raise RuntimeError('Cannot establish native controller state before reload')
    if controller['running']:
        linux(['/usr/local/bin/gc','--city',city,'reload'])
        return 'applied'
    state=controller.get('status','')
    if (state=='stopped' or (state=='' and not controller.get('pid'))):
        return 'deferred_stopped'
    raise RuntimeError('Native controller state is not positively stopped: '+str(controller))


def prepare(data):
    """Export committed source and provision slots before Gas City admission."""
    import workspace
    workspace.repository_guard()
    flags=FLAGS
    def linux(argv, timeout=60):
        r=subprocess.run(['wsl.exe','-d',data['distribution'],'-u',data['user'],
            '--exec',*argv],capture_output=True,text=True, encoding='utf-8',timeout=timeout,creationflags=flags)
        if r.returncode:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip())
        return r.stdout.strip()
    sessions=json.loads(linux(['/usr/local/bin/gc','--city',data['city'],'session','list','--json']))
    if any(s.get('template','').startswith('mu-core/') and not s.get('closed') for s in sessions['sessions']):
        raise RuntimeError('Finish/reconcile current workers before preparing another source wave')
    jobs=json.loads(linux(['/usr/local/bin/gc','--city',data['city'],'bd','--rig','mu-core',
                          'list','--all','--json','--limit','10000']))
    if any(j['status']!='closed' and j.get('metadata',{}).get('gc.routed_to','').startswith('mu-core/') for j in jobs):
        raise RuntimeError('Pending worker work still belongs to the current source wave')
    # Only committed HEAD is transferred. Report dirty inputs excluded from that
    # source identity without modifying them or blocking independent work.
    excluded=workspace.git('status','--porcelain','--untracked-files=all').splitlines()
    head=workspace.git('rev-parse','HEAD')
    if len(jobs)>=10000:
        raise RuntimeError('Task listing is bounded; reconcile pagination before preparing a wave')
    prefix=Path('//wsl.localhost')/data['distribution']
    destination=prefix/data['rig_root'].lstrip('/')/'.local/workspace/dispatch.json'
    existing=reusable_wave(CONTEXT.parent/'waves',jobs,head,destination)
    if existing:
        print(json.dumps({'prepared':True,'reused':True,**existing,'excluded_worktree_status':excluded}))
        return
    branch=workspace.policy()['expected_branch']
    bundle=CONTEXT.parent/('input-'+head+'.bundle')
    if not bundle.exists():
        subprocess.run([workspace.git_executable(),'-c','gc.auto=0','-c','maintenance.auto=false',
            '-C',str(ROOT),'bundle','create',str(bundle),branch],check=True,timeout=120,creationflags=flags)
    prefix=Path('//wsl.localhost')/data['distribution']
    queue=data['queue_origin']; rig=data['rig_root']
    transfer=str(Path(queue).parent/('input-'+head+'.bundle')).replace('\\','/')
    shutil.copyfile(bundle,prefix/transfer.lstrip('/'))
    linux(['git','-c','gc.auto=0','-c','maintenance.auto=false','--git-dir='+queue,
           'fetch',transfer,branch+':refs/heads/'+branch])
    linux(['git','-c','gc.auto=0','-c','maintenance.auto=false','-C',rig,'fetch','origin',branch])
    if linux(['git','-C',rig,'rev-parse',head+'^{commit}']) != head:
        raise RuntimeError('Transferred source identity mismatch')
    if len(jobs)>=10000:
        raise RuntimeError('Task listing is bounded; reconcile pagination before preparing a wave')
    pending=CONTEXT.parent/'preparing-wave.json'
    attempt=json.loads(pending.read_text()) if pending.exists() else {
        'source_head':head,'wave':'mux-wave-'+uuid.uuid4().hex[:12]}
    if attempt['source_head']!=head:
        raise RuntimeError('An incomplete preparation belongs to another source; inspect preparing-wave.json')
    wave=attempt['wave']
    if not re.fullmatch(r'mux-wave-[0-9a-f]{12}',wave):
        raise RuntimeError('Unexpected persisted wave identifier')
    workroot=data['worktree_base']+'/'+wave
    manifest={'source_head':head,'queue_origin':queue,'analysis_tools':data['analysis_tools'],
              'capacity':23,'generation':wave,'wave_bead':wave,'worktree_root':workroot,'city':data['city'],'excluded_worktree_status':excluded}
    config=prefix/data['city'].lstrip('/')/'city.toml'
    text=config.read_text(encoding='utf-8')
    if not any(r.get('name')=='mu-core' for r in tomllib.loads(text).get('rigs',[])):
        raise RuntimeError('The mu-core rig is not registered')
    rendered=set_agent_field(text,'codex','mu-core','work_dir',workroot+'/{{.AgentBase}}')
    rendered=set_agent_field(rendered,'codex','mu-core','max_active_sessions',23)
    maintained=tomllib.loads((ROOT/'.agents/orchestration/city.toml').read_text())
    pre_start=next(p['pre_start'] for p in maintained['patches']['agent']
                   if p['name']=='codex' and p.get('rig')=='mu-core')
    runtime=runtime_tools(data)
    pre_start=[entry.replace('/usr/local/lib/mu-runtime',runtime) for entry in pre_start]
    rendered=set_agent_field(rendered,'codex','mu-core','pre_start',pre_start)
    tomllib.loads(rendered)
    # Persist an explicit native issue ID BEFORE creation, so an interrupted
    # command can be resumed without duplicating an unknown-outcome wave.
    pending.write_text(json.dumps(attempt,indent=2)+'\n',encoding='utf-8')
    if not any(j['id']==wave for j in jobs):
        linux(['/usr/local/bin/gc','--city',data['city'],'bd','--rig','mu-core','create',
            'Worker wave '+head[:12],'--id',wave,'--type','epic','--description',
            'Owner-pinned worker source input. Integrator closes this wave after collecting reviewed owned results.', '--silent'])
    destination=prefix/rig.lstrip('/')/'.local/workspace/dispatch.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    # GC renders hooks into work_dir before pre_start. A native Git worktree must
    # therefore exist BEFORE the new pool path is admitted into city config.
    for slot in range(1,manifest['capacity']+1):
        linux(['python3',runtime+'/provision_worker.py',
            '--rig-root',rig,'--work-dir',workroot+'/codex-'+str(slot),
            '--slot','codex-'+str(slot)],timeout=120)
    config.write_text(rendered,encoding='utf-8',newline='\n')
    reload_outcome=reload_prepared_city(linux,data['city'])
    receipts=CONTEXT.parent/'waves';receipts.mkdir(exist_ok=True)
    (receipts/(wave+'.json')).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    pending.unlink()
    print(json.dumps({'prepared':True,'source_head':head,'wave':wave,'capacity':23,
                      'worktree_root':workroot,'excluded_worktree_status':excluded,'reload':reload_outcome,'provisioning':'native gc worktree ensure before pool admission; pre_start revalidates'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init-context', 'configure', 'prepare', 'dispatch', 'batch', 'batch-status', 'status', 'start', 'stop', 'gc'])
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'init-context':
        if len(args.args)!=1:parser.error('init-context requires one edited JSON example path')
        print(json.dumps(init_context(args.args[0])))
        return 0
    data = context()
    tail = args.args[1:] if args.args[:1] == ['--'] else args.args
    if args.action in ('gc','dispatch','batch','batch-status'):
        if not tail:
            parser.error('gc requires a native command; dispatch requires a task JSON path')
        if args.action!='gc' and len(tail)!=1:
            parser.error('dispatch/batch take one JSON path; batch-status takes one batch ID')
    else:
        if tail:
            parser.error('Extra arguments require the gc action')
        tail = [args.action, '--json']
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    version = subprocess.check_output(command(data, ['version']),
        text=True, encoding='utf-8', creationflags=flags, timeout=15).strip()
    pinned = next(a['version'].removeprefix('v') for a in
        json.loads((ROOT / '.agents/runtime-lock.json').read_text())['assets']
        if a['name'] == 'gascity')
    if version != pinned and args.action not in ('status', 'batch-status', 'stop'):
        raise RuntimeError('Installed Gas City version differs from runtime-lock')
    if args.action in ('configure', 'prepare', 'dispatch', 'batch', 'start', 'gc'):
        verify_boundary(data)
        lock=json.loads((ROOT/'.agents/runtime-lock.json').read_text())
        for name,argv in [('beads',['bd','version']),('dolt',['dolt','version']),('codex',['codex','--version'])]:
            expected=next(a['version'] for a in lock['assets'] if a['name']==name)
            expected=expected.removeprefix('rust-').removeprefix('v')
            checked=subprocess.check_output(['wsl.exe','-d',data['distribution'],'-u',data['user'],
                '--exec','/usr/local/bin/'+argv[0],*argv[1:]],text=True, encoding='utf-8',
                creationflags=flags,timeout=15).strip()
            if not re.search(r'(?<![0-9.])'+re.escape(expected)+r'(?![0-9.\w-])',checked):
                raise RuntimeError(name+' version differs from runtime-lock: '+checked)
    if args.action == 'configure':
        deploy_tools(data)
        configure(data)
        configure_advisers(data)
        check_models(data)
        trust_city_hooks(data)
        return 0
    if args.action in ('prepare','dispatch','batch','start','gc'):
        check_models(data)
    if args.action in ('batch','batch-status'):
        from agent_batch import run_batch,batch_status
        if args.action=='batch':
            ensure_keepalive(data)
            ensure_tmux(data)
            trust_city_hooks(data)
            result=run_batch(data,tail[0],command)
        else:result=batch_status(data,tail[0],command)
        print(json.dumps(result,ensure_ascii=False))
        return 0
    if args.action=='dispatch':
        ensure_tmux(data)
        trust_city_hooks(data)
        return dispatch(data,tail[0])
    if args.action == 'prepare':
        prepare(data)
        return 0
    if args.action == 'start':
        ensure_keepalive(data)
        ensure_tmux(data)
        trust_city_hooks(data)
    try:
        body=sys.stdin.read().replace('\r\n','\n').encode('utf-8') if '--stdin' in tail else None
        result = subprocess.run(command(data, tail), cwd=ROOT,
            input=body,capture_output=True,creationflags=flags, timeout=120)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('Command timed out; outcome is UNKNOWN. Inspect native status, '
                           'session/task IDs and events before retrying a mutation.') from error
    if args.action=='status' and result.returncode==0:
        status=json.loads(result.stdout)
        try:
            live=subprocess.run(command(data,['session','list','--json']),capture_output=True,
                timeout=30,creationflags=flags,check=True)
            status['fresh_sessions']=json.loads(live.stdout)
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            status['fresh_sessions']=None
            status['fresh_sessions_error']=str(error)
        status['native_snapshot_notice']='Native status may be cached/partial; fresh_sessions is a separate current session read. Verify completion by task ID and comments.'
        print(json.dumps(status))
    else:
        sys.stdout.write(result.stdout.decode('utf-8',errors='replace'))
    sys.stderr.write(result.stderr.decode('utf-8',errors='replace'))
    if args.action == 'stop' and result.returncode == 0:
        stop_keepalive()
    return result.returncode


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
