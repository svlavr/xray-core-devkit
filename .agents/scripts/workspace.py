"""Validate installed Xray tools and generate checkout-local ignored host settings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ROOT / '.local/workspace/context.json'
FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
HOST_FILES = ('.local/workspace/context.json', '.codex/config.toml')
PROJECT_KEYS = {'baseline', 'expected_branch', 'integrating_url', 'integrating_branch',
                'public_url', 'public_branch', 'anchor', 'public_push_mode'}


def context_path():
    return ROOT / '.local/workspace/context.json'


def project_settings():
    path = ROOT / '.agents/project.json'
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise RuntimeError('Project settings must be a JSON object')
    unknown = set(value) - PROJECT_KEYS
    if unknown:
        raise RuntimeError('Unknown project settings: ' + ', '.join(sorted(unknown)))
    if any(not isinstance(item, str) or not item for item in value.values()):
        raise RuntimeError('Project settings must contain nonempty string values')
    return value


def policy():
    """Return local selections plus optional user-owned project overrides."""
    path = context_path()
    value = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    if not isinstance(value, dict):
        raise RuntimeError('Host context must be a JSON object')
    project = project_settings()
    for key in ('baseline', 'expected_branch'):
        if key in value:
            project.pop(key, None)
    value.update(project)
    return value


def git_executable():
    direct = Path('C:/Program Files/Git/mingw64/bin/git.exe')
    found = str(direct) if direct.is_file() else shutil.which('git')
    if not found:
        raise RuntimeError('Git executable unavailable')
    return found


def git(*args):
    result = subprocess.run([git_executable(), '--no-optional-locks', '--no-pager', '-c', 'core.fsmonitor=false',
                             '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(ROOT), *args],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding='utf-8',
                            creationflags=FLAGS, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Git check failed: ' + ' '.join(args))
    return result.stdout.strip()


def repository_guard(selection=None):
    p = dict(policy() if selection is None else selection)
    if Path(git('rev-parse', '--show-toplevel')).resolve() != ROOT.resolve():
        raise RuntimeError('Unexpected repository root')
    branch = git('branch', '--show-current')
    if not branch:
        raise RuntimeError('A named working branch is required; detached HEAD is unsupported')
    if p.get('expected_branch', branch) != branch:
        raise RuntimeError('Unexpected working branch; rerun setup after selecting the intended branch')
    baseline = p.get('baseline') or git('rev-parse', 'HEAD')
    if not re.fullmatch(r'[0-9a-fA-F]{40}', baseline):
        raise RuntimeError('Baseline must be a full 40-character commit SHA')
    resolved = git('rev-parse', '--verify', '--end-of-options', baseline + '^{commit}')
    if resolved.lower() != baseline.lower():
        raise RuntimeError('Baseline must identify the exact selected commit')
    git('merge-base', '--is-ancestor', resolved, 'HEAD')
    module = (ROOT / 'go.mod').read_text(encoding='utf-8')
    if not re.search(r'^module\s+github\.com/xtls/xray-core\s*$', module, re.M):
        raise RuntimeError('Wrong Go module; expected github.com/xtls/xray-core')
    p.update(expected_branch=branch, baseline=resolved, baseline_kind='user-selected-comparison')
    return p


def validate():
    from language_policy import WORKER_INSTRUCTIONS
    roles = sorted((ROOT / '.codex/agents').glob('*.toml'))
    skills = sorted((ROOT / '.agents/skills').glob('*/SKILL.md'))
    if len(roles) != 8 or len(skills) != 11:
        raise RuntimeError('Expected 8 domain roles and 11 project skills')
    expected_roles = {'mu_explorer', 'mu_investigator', 'mu_upstream_researcher', 'mu_go_worker',
                      'mu_reviewer', 'mu_critical_reviewer', 'mu_performance_reviewer', 'mu_deep_reviewer'}
    if {path.stem for path in roles} != expected_roles:
        raise RuntimeError('Unexpected domain role inventory')
    expected_skills = {'adversarial-reviewer', 'handoff', 'security-threat-model', 'xray-code-analysis',
                       'xray-core-start', 'xray-fork-android-validation', 'xray-fork-checkpoint',
                       'xray-fork-implement', 'xray-fork-research', 'xray-orchestration', 'xray-public-ci'}
    if {path.parent.name for path in skills} != expected_skills:
        raise RuntimeError('Unexpected project skill inventory')
    for path in roles:
        d = tomllib.loads(path.read_text(encoding='utf-8'))
        name = path.stem
        model = 'gpt-6-luna' if name == 'mu_explorer' else 'gpt-6-astra' if name == 'mu_deep_reviewer' else 'gpt-6.1-sol'
        sandbox = 'workspace-write' if name == 'mu_go_worker' else 'read-only'
        if (d['name'], d['model'], d['model_reasoning_effort'], d['sandbox_mode']) != (name, model, 'high', sandbox):
            raise RuntimeError('Role policy mismatch: ' + name)
        if not d.get('developer_instructions', '').lstrip().startswith(WORKER_INSTRUCTIONS):
            raise RuntimeError('Internal worker language policy mismatch: ' + name)
        if d.get('agents', {}).get('enabled') is not False:
            raise RuntimeError('Nested native agents must remain disabled: ' + name)
    for path in skills:
        parts = path.read_text(encoding='utf-8').split('---', 2)
        if len(parts) != 3:
            raise RuntimeError('Missing skill frontmatter: ' + str(path))
        header = parts[1]
        if not re.search(r'^name: ' + re.escape(path.parent.name) + r'\s*$', header, re.M) or not re.search(r'^description: .+', header, re.M):
            raise RuntimeError('Skill metadata mismatch: ' + str(path))
    if not (ROOT / '.agents/CODEX_PACK.md').is_file():
        raise RuntimeError('Missing toolkit instructions: .agents/CODEX_PACK.md')
    return {'skills': len(skills), 'roles': len(roles)}


def configuration(python, analysis_tools=None, node=None):
    from context_policy import toml_settings
    from language_policy import PRIMARY_INSTRUCTIONS
    quote = lambda value: json.dumps(str(value))
    text = toml_settings() + 'developer_instructions = ' + quote(PRIMARY_INSTRUCTIONS) + '\n\n[features]\nmulti_agent_v2 = true\n\n[agents]\nenabled = true\ndefault_subagent_model = "gpt-6.1-sol"\ndefault_subagent_reasoning_effort = "high"\nmax_concurrent_threads_per_session = 23\ninterrupt_message = true\n'
    for role in sorted((ROOT / '.codex/agents').glob('*.toml')):
        d = tomllib.loads(role.read_text(encoding='utf-8'))
        text += f'\n[agents.{d["name"]}]\ndescription = {quote(d["description"])}\nconfig_file = {quote("agents/" + role.name)}\n'
    go_tools = ['go_workspace', 'go_search', 'go_file_context', 'go_package_api', 'go_symbol_references', 'go_diagnostics']
    profiles = [('xray_gopls_windows', 'gopls', 'windows', go_tools), ('xray_gopls_android', 'gopls', 'android', go_tools),
                ('xray_gitnexus', 'gitnexus', None, ['list_repos', 'query', 'context', 'impact', 'trace', 'check'])]
    for name, backend, profile, allowed in profiles:
        args = [str(ROOT / '.agents/scripts/xray_mcp.py'), backend]
        if profile:
            args += ['--profile', profile]
        enabled = 'false' if profile == 'android' else 'true'
        text += f'\n[mcp_servers.{name}]\nenabled = {enabled}\ndefault_tools_approval_mode = "auto"\ncommand = {quote(python)}\nargs = {json.dumps(args)}\nenabled_tools = {json.dumps(allowed)}\nstartup_timeout_sec = 60\ntool_timeout_sec = 240\n'
    if analysis_tools:
        repomix = Path(analysis_tools) / 'repomix/node_modules/repomix/bin/repomix.cjs'
        if repomix.is_file() and node:
            text += f'\n[mcp_servers.xray_repomix]\nenabled = true\ncommand = {quote(python)}\nargs = {json.dumps([str(ROOT / ".agents/scripts/resource_guard.py"), "--relay", "--", str(node), str(repomix), "--mcp", "--sandbox", str(ROOT)])}\nstartup_timeout_sec = 60\ntool_timeout_sec = 240\n'
    text += '\n[mcp_servers.context7]\nenabled = true\nurl = "https://mcp.context7.com/mcp"\n'
    return text


def capability_status(catalog=None, required=False):
    from context_policy import settings
    path = Path(catalog) if catalog else Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'models_cache.json'
    if not path.is_file():
        if required:
            raise RuntimeError('Local model capability catalog unavailable: ' + str(path))
        return {'status': 'UNKNOWN', 'reason': 'Local model capability catalog unavailable; no online authentication attempted'}
    settings(json.loads(path.read_text(encoding='utf-8')))
    return {'status': 'VERIFIED_LOCAL_CATALOG', 'catalog': str(path),
            'limitation': 'Local catalog does not prove account access or loaded session settings'}


def remote_inventory():
    return {name: {'fetch': git('remote', 'get-url', '--all', name).splitlines(),
                   'push': git('remote', 'get-url', '--push', '--all', name).splitlines()}
            for name in git('remote').splitlines()}


def verify(catalog=None, require_capabilities=False):
    p = repository_guard()
    result = validate()
    capability = capability_status(catalog, require_capabilities)
    ctx = json.loads(context_path().read_text(encoding='utf-8'))
    if Path(ctx['core']).resolve() != ROOT.resolve() or ctx['expected_branch'] != p['expected_branch'] or ctx['baseline'] != p['baseline']:
        raise RuntimeError('Host context is stale; run setup from the current checkout')
    for key in ['python', 'git_executable']:
        if not Path(ctx[key]).is_file():
            raise RuntimeError('Missing host executable: ' + key)
    if not Path(ctx['analysis_tools']).is_dir():
        raise RuntimeError('Analysis tools directory unavailable')
    if ctx.get('node') and not Path(ctx['node']).is_file():
        raise RuntimeError('Missing pinned Node executable; run setup')
    for relative in HOST_FILES:
        host_target(relative)
        if git('ls-files', '--', relative):
            raise RuntimeError('Host settings must never be tracked')
        git('check-ignore', '--', relative)
    config = ROOT / '.codex/config.toml'
    if config.read_text(encoding='utf-8') != configuration(ctx['python'], ctx['analysis_tools'], ctx.get('node')):
        raise RuntimeError('Host config differs from project roles; regenerate with setup')
    return {'status': 'VERIFIED', 'core': str(ROOT), 'expected_branch': p['expected_branch'],
            'baseline': p['baseline'], 'baseline_kind': p['baseline_kind'], **result,
            'model_capabilities': capability, 'external_pack_required': False}


def host_target(relative):
    target = ROOT / relative
    for path in [*reversed(target.parents), target]:
        if path == ROOT or ROOT not in path.parents:
            continue
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise RuntimeError('Host settings must not traverse links/reparse points: ' + str(path))
        if path == target and stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise RuntimeError('Host settings must not alias another file: ' + str(path))
    if not target.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Host settings escape the checkout: ' + relative)
    return target


def setup(analysis_tools, baseline=None, catalog=None, require_capabilities=False):
    selection = project_settings()
    selection.update(baseline=baseline or selection.get('baseline') or git('rev-parse', 'HEAD'),
                     expected_branch=selection.get('expected_branch') or git('branch', '--show-current'))
    p = repository_guard(selection)
    validate()
    tools = analysis_tools.resolve()
    if not tools.is_dir():
        raise RuntimeError('Analysis tools directory unavailable')
    capability_status(catalog, require_capabilities)
    for relative in HOST_FILES:
        host_target(relative)
        if git('ls-files', '--', relative):
            raise RuntimeError('Refusing tracked host file: ' + relative)
        try:
            git('check-ignore', '--', relative)
        except RuntimeError as error:
            raise RuntimeError('Host file must already be ignored by checkout rules: ' + relative) from error
    if (ROOT / '.codex/config.toml').exists() and not context_path().is_file():
        raise RuntimeError('Existing local Codex config has no toolkit context; preserve it before setup')
    ctx = {'schema': 1, 'core': str(ROOT), 'baseline': p['baseline'], 'baseline_kind': p['baseline_kind'],
           'expected_branch': p['expected_branch'], 'remotes': remote_inventory(),
           'git_executable': git_executable(), 'python': sys.executable, 'analysis_tools': str(tools),
           'node': shutil.which('node')}
    content = configuration(sys.executable, tools, ctx['node'])
    config = ROOT / '.codex/config.toml'
    if config.exists():
        old = json.loads(context_path().read_text(encoding='utf-8'))
        if Path(old.get('core', '')).resolve() != ROOT.resolve():
            raise RuntimeError('Existing host context belongs to another checkout')
        digest = hashlib.sha256(config.read_bytes()).hexdigest()
        expected = old.get('generated_config_sha256')
        if not expected:
            prior = configuration(old['python'], old['analysis_tools'], old.get('node'))
            expected = hashlib.sha256(prior.encode('utf-8')).hexdigest()
        if expected != digest:
            raise RuntimeError('Local Codex config was edited; preserve those edits before regeneration')
    ctx['generated_config_sha256'] = hashlib.sha256(content.encode('utf-8')).hexdigest()
    context_path().parent.mkdir(parents=True, exist_ok=True)
    config.parent.mkdir(parents=True, exist_ok=True)
    context_path().write_text(json.dumps(ctx, indent=2) + '\n', encoding='utf-8', newline='\n')
    config.write_text(content, encoding='utf-8', newline='\n')
    return verify(catalog, require_capabilities)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'verify', 'validate'])
    parser.add_argument('--analysis-tools', type=Path)
    parser.add_argument('--baseline', help='Full selected comparison commit SHA; defaults to current HEAD')
    parser.add_argument('--catalog', type=Path, help='Read-only local model capability catalog')
    parser.add_argument('--require-capabilities', action='store_true', help='Fail if no local model catalog is available')
    args = parser.parse_args()
    try:
        if args.action == 'setup':
            if args.analysis_tools is None:
                parser.error('setup requires --analysis-tools')
            result = setup(args.analysis_tools, args.baseline, args.catalog, args.require_capabilities)
        else:
            result = verify(args.catalog, args.require_capabilities) if args.action == 'verify' else validate()
        print(json.dumps(result))
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
