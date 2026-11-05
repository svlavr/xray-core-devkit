"""Load the selected Core competency from its authoritative project TOML bytes."""
import hashlib
import json
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
# Custom-agent capability reductions documented at
# https://learn.chatgpt.com/docs/agent-configuration/subagents
# These may disable inherited capabilities, never enable permissions or tools.
SUPPORTED_FEATURES = {'shell_tool', 'apps', 'plugins', 'memories', 'request_permissions_tool'}

PRESET_PATH = '.agents/orchestration/model-presets.json'
PRESET_ROLES = {'native-write-fix': 'mu_go_worker', 'native-accounting-review': 'mu_reviewer', 'delivery-evidence-review': 'mu_behavior_reviewer', 'tool-update-evidence': 'mu_upstream_researcher', 'existing-writer-solution': 'mu_solution_researcher'}
PRESET_KINDS = {'native-write-fix': ['implement'], 'native-accounting-review': ['review'], 'delivery-evidence-review': ['review'], 'tool-update-evidence': ['review', 'explore'], 'existing-writer-solution': ['review', 'explore']}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()


def preset_policy(root=None):
    root=Path(root or ROOT).resolve();path=root/PRESET_PATH
    if not path.is_file() or path.resolve()!=path.absolute() or path.stat().st_nlink!=1:
        raise ValueError('Missing or aliased model preset policy')
    raw=path.read_bytes();policy=json.loads(raw)
    if not isinstance(policy,dict):raise ValueError('Unsupported public model preset catalog')
    entries=policy.get('presets',{})
    if policy.get('schema')!=1 or not isinstance(entries,dict) or set(entries)!=set(PRESET_ROLES):raise ValueError('Unsupported public model preset catalog')
    for name,entry in entries.items():
        if not isinstance(entry,dict):raise ValueError('Invalid bounded model preset: '+name)
        if (entry.get('role')!=PRESET_ROLES[name] or entry.get('model')!='gpt-6.1-terra' or entry.get('effort')!='high'
                or not isinstance(entry.get('kinds'),list) or not entry['kinds']
                or entry['kinds']!=PRESET_KINDS[name]
                or not isinstance(entry.get('scope'),str) or not entry['scope'].strip()
                or not isinstance(entry.get('acceptance'),list) or not entry['acceptance']
                or any(not isinstance(item,str) or not item.strip() for item in entry['acceptance'])
                or not isinstance(entry.get('evidence'),dict)
                or entry['evidence'].get('type')!='bounded-public-consumer-fixture'
                or not isinstance(entry['evidence'].get('references'),list) or not entry['evidence']['references']
                or any(not isinstance(ref,str) or not re.fullmatch(r'docs/[A-Za-z0-9_.-]+\.md',ref) for ref in entry['evidence']['references'])):
            raise ValueError('Invalid bounded model preset: '+name)
    return entries,hashlib.sha256(raw).hexdigest()


def selection_hash(profile):
    return canonical_hash({key:profile[key] for key in ('role','profile_sha256','preset','preset_policy_sha256',
        'preset_sha256','model_policy_sha256','model','effort','selection_request')})


def select_profile(name,root=None,*,task=None):
    """Apply an explicit initial preset; the coordinator owns semantic matching."""
    profile=load_profile(name,root)
    task=task or {}
    if 'preset' not in task:return profile
    preset=task['preset']
    if not isinstance(preset,str) or preset not in PRESET_ROLES:raise ValueError('Unknown Xray model preset: '+str(preset))
    entries,policy_sha=preset_policy(root);entry=entries[preset]
    if (name!=entry['role'] or task.get('kind') not in entry['kinds'] or task.get('bounded') is not True
            or task.get('cross_owner',False) is not False):
        raise ValueError('Model preset requires its exact role, compatible kind, bounded=true and no cross-owner scope: '+preset)
    request={key:task[key] for key in ('preset','kind','bounded','cross_owner') if key in task}
    root=Path(root or ROOT).resolve()
    profile.update(preset=preset,preset_policy_path=PRESET_PATH,preset_policy_sha256=policy_sha,
        preset_sha256=canonical_hash(entry),model_policy_sha256=hashlib.sha256((root/'.agents/orchestration/models.json').read_bytes()).hexdigest(),
        selection_request=request,model=entry['model'],effort=entry['effort'])
    profile['selection_sha256']=selection_hash(profile)
    profile['developer_instructions']+=('\n\nInitial bounded model preset: '+preset+'. Preset policy SHA-256: '+policy_sha+
        '. Preset entry SHA-256: '+profile['preset_sha256']+'.\nScope: '+entry['scope']+
        '\nAcceptance:\n'+'\n'.join('- '+item for item in entry['acceptance'])+
        '\nThis bounded selection does not promote the whole role or authorize work outside the assigned task.')
    return profile


def override_root(value):
    """Read a CLI override's TOML key independently of its possibly bare string value."""
    quote=None;escaped=False
    for index,character in enumerate(value):
        if escaped:
            escaped=False
        elif quote=='"' and character=='\\':
            escaped=True
        elif quote:
            if character==quote:quote=None
        elif character in ('"',"'"):
            quote=character
        elif character=='=':
            key=value[:index].strip()
            try:
                return next(iter(tomllib.loads(key+' = false')))
            except (tomllib.TOMLDecodeError,StopIteration) as error:
                raise ValueError('Invalid CLI configuration key: '+key) from error
    return None


def feature_reductions(features):
    if not isinstance(features, dict) or any(key not in SUPPORTED_FEATURES or value is not False
                                            for key, value in features.items()):
        raise ValueError('Role feature overrides must be documented capability reductions (false)')
    return features


def load_profile(name, root=None):
    root = Path(root or ROOT).resolve()
    if not isinstance(name, str) or not re.fullmatch(r'mu_[a-z_]+', name):
        raise ValueError('Unknown Xray role: ' + str(name))
    module=root/'go.mod'
    if module.is_file():
        if not re.search(r'^module\s+github\.com/xtls/xray-core\s*$', module.read_text(encoding='utf-8'), re.M):
            raise ValueError('Role root is not Xray Core')
    elif not (root/'devkit.py').is_file():
        raise ValueError('Role root is not an installed source, frozen source bundle or standalone DevKit catalog')
    path = root / '.codex/agents' / (name + '.toml')
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError('Unknown or escaping Core role: ' + name)
    raw = path.read_bytes()
    profile = tomllib.loads(raw.decode('utf-8'))
    policy = json.loads((root / '.agents/orchestration/models.json').read_text(encoding='utf-8'))
    model = profile.get('model')
    if profile.get('name') != name or not profile.get('description') or not profile.get('developer_instructions', '').strip():
        raise ValueError('Incomplete or mismatched Core role: ' + name)
    if model not in {route['model'] for route in policy.values()} or profile.get('model_reasoning_effort') != 'high':
        raise ValueError('Unsupported role model or effort: ' + name)
    if (model == policy['deep']['model']) != (name == 'mu_deep_reviewer'):
        raise ValueError('Astra is reserved for mu_deep_reviewer')
    if (model == policy['explore']['model']) != (name == 'mu_explorer'):
        raise ValueError('Luna is reserved for mu_explorer')
    if profile.get('agents', {}).get('enabled') is not False:
        raise ValueError('Role must disable nested agents: ' + name)
    features = feature_reductions(profile.get('features', {}))
    return {'role': name, 'description': profile['description'], 'profile_path': path.relative_to(root).as_posix(),
            'profile_sha256': hashlib.sha256(raw).hexdigest(), 'profile_toml': raw.decode('utf-8'),
            'profile_root': str(root), 'context_root': str(root / '.local/workspace'),
            'skills_root': str(root / '.agents/skills'), 'model': model,
            'effort': profile['model_reasoning_effort'], 'developer_instructions': profile['developer_instructions'],
            'features': features}


def list_profiles(root=None):
    """Expose actual descriptions for main's semantic selection; never classify task text."""
    root = Path(root or ROOT).resolve()
    from workspace import MANAGED_ROLES
    return [load_profile(name, root) for name in sorted(MANAGED_ROLES)]


def configuration_args(profile):
    """Apply only executable competency settings; permissions and tools stay inherited."""
    if profile.get('effort')!='high':raise ValueError('Selected competency effort must remain high')
    if profile.get('preset'):
        if profile.get('model')!='gpt-6.1-terra' or profile.get('selection_sha256')!=selection_hash(profile):
            raise ValueError('Selected model preset identity changed')
    elif profile.get('model') not in {'gpt-6.1-sol','gpt-6-luna','gpt-6-astra'}:
        raise ValueError('A non-default model requires an approved preset')
    settings = {'model': profile['model'], 'model_reasoning_effort': profile['effort'],
                'developer_instructions': profile['developer_instructions'], 'agents.enabled': False}
    settings.update({'features.' + name: value for name, value in feature_reductions(profile.get('features', {})).items()})
    return [argument for key, value in settings.items() for argument in ('-c', key + '=' + json.dumps(value,ensure_ascii=False))]
