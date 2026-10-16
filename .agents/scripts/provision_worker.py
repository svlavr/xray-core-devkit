"""Gas City pre_start adapter: provision a source-pinned worker slot natively."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from worker_context import setup
from runtime_hooks import trust


def provision(rig, workdir, slot):
    rig=rig.resolve(); workdir=workdir.resolve()
    manifest=json.loads((rig/'.local/workspace/dispatch.json').read_text())
    match=re.fullmatch(r'codex-([1-9][0-9]*)',slot)
    if not match or int(match[1])>manifest['capacity']:
        raise RuntimeError('Unexpected worker slot')
    root=Path(manifest['worktree_root']).resolve()
    if workdir != root/slot or root.is_relative_to(rig):
        raise RuntimeError('Worker path must be a direct child outside the rig checkout')
    generation=manifest['generation']
    if not re.fullmatch(r'[a-zA-Z0-9-]+',generation):
        raise RuntimeError('Unexpected dispatch generation')
    branch=f'codex/workers/{generation}/{slot}'
    cmd=['/usr/local/bin/gc','worktree','ensure','--repo',str(rig),'--root',str(root),
         '--path',str(workdir),'--branch',branch,'--base',manifest['source_head'],
         '--base-sha',manifest['source_head'],'--bead',manifest['wave_bead'],
         '--owner','mu-integrator','--creator','mu-worker-pre-start','--generation',generation,
         '--store-ref',str(rig/'.beads'),'--json']
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    native=json.loads(result.stdout)
    configured=setup(workdir,manifest['source_head'],manifest['queue_origin'],Path(manifest['analysis_tools']))
    hooks=trust(workdir,Path(manifest['city']))
    print(json.dumps({'native_worktree':native,'worker_context':configured,'reviewed_hooks':hooks}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rig-root',type=Path,required=True)
    p.add_argument('--work-dir',type=Path,required=True)
    p.add_argument('--slot',required=True)
    a=p.parse_args()
    provision(a.rig_root,a.work_dir,a.slot)
