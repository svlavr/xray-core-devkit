"""Generate isolated worker host context without weakening the primary guard."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from language_policy import WORKER_INSTRUCTIONS


def scoped_mcp_args(config):
    """Pass the generated worker MCP layer even when ignored project config is skipped."""
    result=[]
    def component(value):
        # Codex's override parser requires an unquoted top-level root. Keep all
        # ordinary TOML identifiers plain; quote only names containing dots etc.
        return value if re.fullmatch(r'[A-Za-z0-9_-]+',value) else json.dumps(value,ensure_ascii=False)
    def flatten(value,path):
        for name,item in value.items():
            keys=(*path,name)
            if isinstance(item,dict):flatten(item,keys)
            else:result.extend(('-c','.'.join(component(key) for key in keys)+'='+json.dumps(item,ensure_ascii=False)))
    flatten(config.get('mcp_servers',{}),('mcp_servers',))
    return result


def adviser_configuration(root, source_head, sources):
    """Read-only evidence roots use public retrieval without an invented Go workspace."""
    guidance = (WORKER_INSTRUCTIONS + '\nThis is a frozen external advisory input bundle. '
        'No source edits, Git writes, publication or nested workers. '
        'Remote Context7, grep.app and exa_public_research receive public identifiers/questions/URLs only; '
        'never send private source, contracts, credentials or logs. '
        'Use original sources and distinguish unavailable evidence from a successful check. '
        'Return your result only on the assigned native bead. Source HEAD: ' + source_head +
        '. Assigned source directories: ' + ', '.join(sources))
    return ('developer_instructions = ' + json.dumps(guidance,ensure_ascii=False) + '\n[agents]\nenabled = false\n' +
        public_research_config())


def public_research_config():
    return '''
[mcp_servers.context7]
enabled = true
url = "https://mcp.context7.com/mcp"
startup_timeout_sec = 60
tool_timeout_sec = 60
[mcp_servers.grep_app]
enabled = true
default_tools_approval_mode = "auto"
url = "https://mcp.grep.app"
enabled_tools = ["searchGitHub"]
startup_timeout_sec = 60
tool_timeout_sec = 60
[mcp_servers.exa_public_research]
enabled = true
url = "https://mcp.exa.ai/mcp?tools=web_search_exa,web_fetch_exa"
enabled_tools = ["web_search_exa", "web_fetch_exa"]
startup_timeout_sec = 45
tool_timeout_sec = 45
'''


def setup(repo, base, queue_origin, tools):
    repo = repo.resolve()
    executable = shutil.which('git')
    def git(*args):
        return subprocess.check_output([executable, '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
            '-C', str(repo), *args], text=True, encoding='utf-8', timeout=20,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).strip()
    if Path(git('rev-parse','--show-toplevel')).resolve() != repo:
        raise RuntimeError('Worker root is not a repository root')
    if not Path(queue_origin).is_absolute() or not Path(queue_origin).is_dir():
        raise RuntimeError('Worker origin must be the prepared local queue')
    if git('remote','get-url','origin') != queue_origin or git('remote','get-url','--push','origin') != queue_origin:
        raise RuntimeError('Worker must exchange commits only with its local queue')
    if git('remote').splitlines() != ['origin']:
        raise RuntimeError('Worker has additional remotes; owner review required')
    if not re.search(r'^module\s+github\.com/xtls/xray-core\s*$', (repo/'go.mod').read_text(encoding='utf-8'), re.M):
        raise RuntimeError('Wrong worker module')
    base_sha = git('rev-parse', base+'^{commit}')
    git('merge-base','--is-ancestor',base_sha,'HEAD')
    for name in ['.local/workspace/context.json','.local/workspace/worker.json','.codex/config.toml']:
        if git('ls-files','--',name):
            raise RuntimeError('Host settings cannot overwrite tracked files')
        git('check-ignore','--',name)
        target = repo/name
        if target.resolve() != target.absolute() or (target.exists() and target.stat().st_nlink != 1):
            raise RuntimeError('Worker host settings must not alias another path')
    tools = tools.resolve()
    binary = tools/'bin'/('gopls.exe' if os.name=='nt' else 'gopls')
    if not binary.is_file():
        raise RuntimeError('Worker gopls is unavailable')
    ctx = {'core':str(repo),'worker':True,'source_base':base_sha,'queue_origin':queue_origin,
           'git_executable':executable,'python':sys.executable,'analysis_tools':str(tools),
           'node':shutil.which('node')}
    path=repo/'.local/workspace';path.mkdir(parents=True,exist_ok=True)
    (path/'context.json').write_text(json.dumps(ctx,indent=2)+'\n',encoding='utf-8')
    (path/'worker.json').write_text(json.dumps({'base':base_sha,'repo':str(repo),'queue_origin':queue_origin})+'\n',encoding='utf-8')
    profile='windows' if os.name=='nt' else 'linux'
    adapter=Path(__file__).with_name('go_mcp.py').resolve()
    if not adapter.is_file() or not adapter.with_name('resource_guard.py').is_file():
        raise RuntimeError('The portable Go MCP adapter dependency set is missing')
    args=[str(adapter),'--binary',str(binary),'--root',str(repo)]
    guidance=(WORKER_INSTRUCTIONS + '\n\nThis is an owner-prepared isolated Xray Core worker copy. '
        'Read .local/workspace/worker.json for its exact base/local queue. '
        'Read docs/PROJECT_SCOPE.md for the owner-selected scope and accepted contracts. The integration and publication guards belong to the integrator. '
        'Verify actual go_workspace against this working root. Follow the dispatched owned paths; '
        'local worker commits are handoff artifacts, never publish to GitHub or spawn nested workers. '
        'Run validation through the deployed resource_guard.py with --cwd pointing to this checkout '
        'and --transient pointing to its .local/host/transient, followed by -- and the command. '
        'Keep logs and output artifacts outside that disposable scratch; preserve shared Go caches. '
        'Remote Context7, grep.app and exa_public_research receive public identifiers/questions/URLs only; '
        'never send private source, contracts, credentials or logs. '
        'Exa web_search_exa requires query and objective; web_fetch_exa takes urls. The two-tool Exa profile adds no model execution or permission authority; actual access follows the parent session permissions and approvals. '
        'Use retrieved original sources as evidence; model-generated summaries and search results do not prove '
        'tested behavior or implementation completeness. Do not invoke research agents or nested workers; '
        'return deciding evidence and explicit unknowns to the coordinator.')
    config='developer_instructions = '+json.dumps(guidance,ensure_ascii=False)+'\n\n[agents]\nenabled = false\n\n[mcp_servers.xray_gopls_worker]\nenabled = true\n'
    config+='command = '+json.dumps(sys.executable,ensure_ascii=False)+'\nargs = '+json.dumps(args,ensure_ascii=False)+'\n'
    config+='startup_timeout_sec = 60\ntool_timeout_sec = 240\n'
    config+='enabled_tools = ["go_workspace", "go_search", "go_file_context", "go_package_api", "go_symbol_references", "go_diagnostics"]\n'
    config+='[mcp_servers.xray_gopls_worker.env]\nGOOS = '+json.dumps(profile)+'\nGOARCH = "amd64"\nCGO_ENABLED = "0"\nGOFLAGS = "-mod=readonly"\nGOMAXPROCS = "2"\n'
    config+=public_research_config()
    (repo/'.codex').mkdir(exist_ok=True)
    (repo/'.codex/config.toml').write_text(config,encoding='utf-8',newline='\n')
    return {'status':'WORKER_CONFIGURED','root':str(repo),'base':base_sha,'profile':profile}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--base',required=True)
    p.add_argument('--queue-origin',required=True)
    p.add_argument('--analysis-tools',type=Path,required=True)
    a=p.parse_args()
    try:
        print(json.dumps(setup(a.repo,a.base,a.queue_origin,a.analysis_tools)))
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        print('BLOCKED: '+str(error),file=sys.stderr)
        raise SystemExit(1)
