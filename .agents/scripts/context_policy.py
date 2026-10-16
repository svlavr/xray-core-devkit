"""Model-catalog checked context settings for the configured model family."""
import json
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / 'orchestration/context.json'


def settings(catalog=None):
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    for key in ('window', 'effective_percent', 'compact_at_effective_percent'):
        if isinstance(policy.get(key), bool) or not isinstance(policy.get(key), int):
            raise RuntimeError('Context policy needs integer ' + key)
    if (policy['window'] <= 0 or not 1 <= policy['effective_percent'] <= 100
            or not 1 <= policy['compact_at_effective_percent'] <= 100
            or policy.get('scope') not in ('total', 'body_after_prefix')
            or not isinstance(policy.get('models'), list) or not policy['models']
            or any(not isinstance(name, str) or not name for name in policy['models'])):
        raise RuntimeError('Invalid context policy')
    if catalog is not None:
        if not isinstance(catalog, dict) or not isinstance(catalog.get('models'), list):
            raise RuntimeError('Invalid local model capability catalog')
        models = {m['slug']: m for m in catalog['models'] if isinstance(m, dict) and 'slug' in m}
        for name in policy['models']:
            model = models.get(name, {})
            window = model.get('max_context_window', model.get('context_window', 0))
            if (not isinstance(window, int) or isinstance(window, bool) or window < policy['window']
                    or model.get('effective_context_window_percent') != policy['effective_percent']):
                raise RuntimeError('Context policy requires a fresh model-capability review: ' + name)
    effective = policy['window'] * policy['effective_percent'] // 100
    return {'model_context_window': policy['window'],
            'model_auto_compact_token_limit': effective * policy['compact_at_effective_percent'] // 100,
            'model_auto_compact_token_limit_scope': policy['scope']}


def toml_settings():
    return ''.join(key + ' = ' + json.dumps(value) + '\n' for key, value in settings().items())
