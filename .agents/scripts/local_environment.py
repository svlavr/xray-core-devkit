"""Host values stay in the checkout-local ignored context."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ROOT / '.local/workspace/context.json'


def host():
    data = json.loads(CONTEXT.read_text(encoding='utf-8'))
    if Path(data['core']).resolve() != ROOT.resolve():
        raise RuntimeError('Host context belongs to another checkout')
    return data


def git(*args, timeout=20):
    return subprocess.check_output(
        [host()['git_executable'], '--no-optional-locks', '--no-pager', '-c', 'core.fsmonitor=false',
         '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'core.hooksPath=' + str(ROOT / '.local/disabled-hooks'),
         '-C', str(ROOT), *args], stdin=subprocess.DEVNULL,
        text=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        timeout=timeout).strip()
