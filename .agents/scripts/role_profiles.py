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
    settings = {'model': profile['model'], 'model_reasoning_effort': profile['effort'],
                'developer_instructions': profile['developer_instructions'], 'agents.enabled': False}
    settings.update({'features.' + name: value for name, value in feature_reductions(profile.get('features', {})).items()})
    return [argument for key, value in settings.items() for argument in ('-c', key + '=' + json.dumps(value,ensure_ascii=False))]
