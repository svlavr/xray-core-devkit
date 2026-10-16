"""Explicit automatic model routing from the coordinator's scoped work packet."""
import json
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / 'orchestration/models.json'


def select_route(task):
    policy=json.loads(POLICY.read_text())
    kind=task.get('kind')
    if kind not in ('explore','implement','review','deep'):
        raise ValueError('Choose a work kind: explore, implement, review, or deep')
    if task.get('blocker') in ('missing_input','access','environment','validation_not_run'):
        return {'action':'NEEDS_CONTEXT','reason':task['blocker']}
    previous=task.get('previous_model')
    unresolved=task.get('blocker')=='unresolved_technical'
    if previous=='gpt-6-astra' and unresolved:
        return {'action':'NEEDS_CONTEXT','reason':'Astra already examined this discriminator; obtain new evidence instead of repeating it'}
    if kind=='deep' or (previous=='gpt-6.1-sol' and unresolved):
        if not unresolved or previous!='gpt-6.1-sol' or not task.get('discriminator') or not task.get('evidence'):
            raise ValueError('Astra requires a named unresolved discriminator and evidence from a Sol 6.1 attempt')
        route='deep'
    elif kind=='explore' and task.get('bounded') is True and not task.get('cross_owner') and not unresolved:
        route='explore'
    elif kind=='implement':
        route='implement'
    else:
        route='review'
    return {'action':'DISPATCH','route':route,**policy[route]}


def validate_models(config):
    """Astra is allowed only in the single city-scoped deep-adviser pool."""
    policy=json.loads(POLICY.read_text())
    default=config.get('providers',{}).get(config.get('workspace',{}).get('provider'),{}).get('option_defaults',{})
    if default.get('model')!=policy['implement']['model'] or default.get('effort')!='high':
        raise RuntimeError('Worker default must be explicit Sol 6.1 High, never inherited Astra')
    deep_count=0
    for agent in config.get('agent',[]):
        if agent.get('start_command'):
            if agent.get('name')=='control-dispatcher' and agent.get('process_names')==['gc']:
                continue
            raise RuntimeError('Custom agent start command needs a model audit: '+agent['name'])
        provider=agent.get('provider') or config['workspace'].get('provider')
        spec=config.get('providers',{}).get(provider,{})
        options={**spec.get('option_defaults',{}),**agent.get('option_defaults',{})}
        model=options.get('model');effort=options.get('effort')
        if model not in {r['model'] for r in policy.values()} or effort!='high':
            raise RuntimeError('Unpinned/unsupported agent model or effort: '+agent['name'])
        if model=='gpt-6-astra' and (agent['name']!='mu-deep' or agent.get('dir')
                                   or agent.get('max_active_sessions')!=1):
            raise RuntimeError('Astra may only run in the single city-scoped mu-deep pool')
        if model=='gpt-6-astra':
            deep_count+=1
            if deep_count>1:
                raise RuntimeError('Only one city-scoped Astra pool is permitted')
        limit=agent.get('max_active_sessions',1)
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=23:
            raise RuntimeError('Agent pool capacity must be bounded to 1..23: '+agent['name'])
    return True
