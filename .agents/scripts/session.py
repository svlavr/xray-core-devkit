"""Run Codex with the verified local layer as explicit per-invocation settings."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys,tomllib
from workspace import ROOT, verify
from resource_guard import run

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

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--core',type=Path,default=ROOT)
    parser.add_argument('codex_args',nargs=argparse.REMAINDER);args=parser.parse_args()
    core=args.core.resolve()
    if core!=ROOT:raise RuntimeError('Use the launcher inside the requested checkout')
    verify()
    cli=shutil.which('codex')
    if not cli:raise SystemExit('Codex CLI unavailable')
    tail=args.codex_args[1:] if args.codex_args[:1]==['--'] else args.codex_args
    command=[cli,'-C',str(core),*configuration_args(core),*tail]
    # Parent model/effort/auth and global files remain untouched.
    result=run(command,cwd=core,timeout=None,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    raise SystemExit(result.returncode)
