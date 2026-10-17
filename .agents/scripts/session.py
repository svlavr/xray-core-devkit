"""Run Codex with the verified local layer as explicit per-invocation settings."""
from pathlib import Path
import argparse,json,re,shutil,subprocess,tomllib
from workspace import ROOT, verify
from resource_guard import run
from model_router import resolve_assignment
from role_profiles import configuration_args as profile_args, list_profiles, override_root

def configuration_args(core):
    cfg=tomllib.loads((core/'.codex/config.toml').read_text(encoding='utf-8'))
    for role in cfg.get('agents',{}).values():
        if isinstance(role,dict) and 'config_file' in role:
            role['config_file']=str((core/'.codex'/role['config_file']).resolve())
    args=[]
    def flatten(value,prefix=''):
        for name,item in value.items():
            key=prefix+name
            if isinstance(item,dict):flatten(item,key+'.')
            else:args.extend(['-c',key+'='+json.dumps(item,ensure_ascii=False)])
    flatten(cfg)
    return args

def verify_worker(core):
    """Check an owner-prepared local queue copy instead of applying the primary guard."""
    marker=json.loads((core/'.local/workspace/worker.json').read_text(encoding='utf-8'))
    context=json.loads((core/'.local/workspace/context.json').read_text(encoding='utf-8'))
    if (not re.fullmatch(r'[0-9a-f]{40}',marker['base'])
            or Path(marker['repo']).resolve()!=core or not context.get('worker')
            or Path(context['core']).resolve()!=core or context['source_base']!=marker['base']
            or context['queue_origin']!=marker['queue_origin']):
        raise RuntimeError('Worker root/base/local queue context mismatch')
    queue=Path(marker['queue_origin'])
    if not queue.is_absolute() or not queue.is_dir():
        raise RuntimeError('Worker queue must be an existing absolute local directory')
    executable=context['git_executable']
    def git(*arguments):
        return subprocess.check_output([executable,'--no-pager','-c','gc.auto=0','-c','maintenance.auto=false',
            '-C',str(core),*arguments],text=True,encoding='utf-8',timeout=20,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).strip()
    if Path(git('rev-parse','--show-toplevel')).resolve()!=core:
        raise RuntimeError('Worker repository root mismatch')
    if git('remote').splitlines()!=['origin']:
        raise RuntimeError('Worker may only use its prepared local queue remote')
    for arguments in [('remote','get-url','origin'),('remote','get-url','--push','origin')]:
        if git(*arguments)!=marker['queue_origin']:
            raise RuntimeError('Worker local queue remote mismatch')
    if git('rev-parse',marker['base']+'^{commit}')!=marker['base']:
        raise RuntimeError('Worker base must be an exact commit')
    git('merge-base','--is-ancestor',marker['base'],'HEAD')
    if not re.search(r'^module\s+github\.com/xtls/xray-core\s*$', (core/'go.mod').read_text(encoding='utf-8'), re.M):
        raise RuntimeError('Wrong worker Go module')
    config=tomllib.loads((core/'.codex/config.toml').read_text(encoding='utf-8'))
    mcp=config.get('mcp_servers',{}).get('xray_gopls_worker',{})
    arguments=mcp.get('args',[])
    if (mcp.get('enabled') is not True or '--root' not in arguments
            or arguments.index('--root')+1>=len(arguments)
            or Path(arguments[arguments.index('--root')+1]).resolve()!=core):
        raise RuntimeError('Worker Go MCP is not bound to this source root')
    if config.get('agents',{}).get('enabled') is not False:
        raise RuntimeError('Worker must disable nested agents')
    return {'status':'WORKER_VERIFIED','root':str(core),'base':marker['base']}


def build_command(cli,core,tail,role=None,task=None,execute=False):
    command=[cli,'-C',str(core),*configuration_args(core)]
    if execute:
        command.append('exec')
    if role:
        task=dict(task or {})
        if 'role' in task and task['role']!=role:
            raise ValueError('CLI and task role differ')
        task.setdefault('kind','review');task['role']=role
        assignment=resolve_assignment(task,core)
        if assignment['action']!='DISPATCH':
            raise ValueError('Role execution needs context: '+assignment['reason'])
        # A later CLI flag must not silently replace the attested competency settings.
        for index,argument in enumerate(tail):
            if (argument in ('-m','--model','-p','--profile','-C','--cd') or argument.startswith(('--model=','--profile=','--cd='))
                    or argument.startswith(('-m','-p','-C')) and not argument.startswith('--')):
                raise ValueError('Role execution cannot override its model, profile or source root')
            value=tail[index+1] if argument in ('-c','--config') and index+1<len(tail) else (
                argument.split('=',1)[1] if argument.startswith('--config=') else
                argument[2:] if argument.startswith('-c') else '')
            key=override_root(value)
            if key=='mcp_servers':
                # A selected role may disable tools; later CLI settings must not
                # substitute the attested adapter, arguments or source root.
                try:
                    servers=tomllib.loads(value)['mcp_servers']
                except (tomllib.TOMLDecodeError,KeyError) as error:
                    raise ValueError('Role execution cannot replace MCP identities') from error
                if (not isinstance(servers,dict) or not servers
                        or any(not isinstance(server,dict) or server!={'enabled':False}
                               for server in servers.values())):
                    raise ValueError('Role execution permits only MCP enabled=false reductions')
            if key in ('model','model_reasoning_effort','developer_instructions','agents','features'):
                raise ValueError('Role execution cannot override competency settings: '+key)
        command.extend(profile_args(assignment))
    command.extend(tail)
    return command


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--core',type=Path,default=ROOT)
    parser.add_argument('--role',help='Apply this project TOML as CLI profile execution, not native agent_type admission')
    parser.add_argument('--task',type=Path,help='Assignment JSON, including evidence for a deep role')
    parser.add_argument('--list-roles',action='store_true',help='Show actual competency descriptions for semantic selection')
    parser.add_argument('--exec',dest='exec_args',nargs=argparse.REMAINDER,help='Run codex exec with these arguments')
    parser.add_argument('codex_args',nargs=argparse.REMAINDER);args=parser.parse_args(argv)
    core=args.core.resolve()
    if core!=ROOT:raise RuntimeError('Use the launcher inside the requested checkout')
    if args.list_roles:
        print(json.dumps([{key:profile[key] for key in ('role','description','model','effort','profile_path','profile_sha256')}
                          for profile in list_profiles(core)],indent=2));return 0
    if (core/'.local/workspace/worker.json').is_file():verify_worker(core)
    else:verify()
    cli=shutil.which('codex')
    if not cli:raise SystemExit('Codex CLI unavailable')
    tail=args.exec_args if args.exec_args is not None else args.codex_args
    tail=tail[1:] if tail[:1]==['--'] else tail
    task=json.loads(args.task.read_text(encoding='utf-8')) if args.task else None
    if task and not args.role:parser.error('--task requires --role')
    command=build_command(cli,core,tail,args.role,task,args.exec_args is not None)
    # No-role launches retain the normal configured parent settings. Role launches are explicit children.
    result=run(command,cwd=core,timeout=None,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return result.returncode


if __name__=='__main__':
    raise SystemExit(main())
