#!/usr/bin/env python3
"""Bind one native Gas City trigger to its immutable competency before Codex starts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verified(path, expected):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path.absolute() or not path.is_file():
        raise RuntimeError('Launch input is missing or linked: ' + str(path))
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise RuntimeError('Launch input hash mismatch: ' + str(path))
    return raw


def read_launch(path, expected):
    launch = json.loads(verified(path, expected))
    root = Path(launch['tooling_root'])
    for relative, entry in launch['files'].items():
        target = root / relative
        if not target.resolve().is_relative_to(root.resolve()):
            raise RuntimeError('Launch input escapes tooling root')
        verified(target, entry['sha256'])
    if launch['mode'] != 'implement':
        runtime = Path(launch['run_root'])
        if (not runtime.is_absolute() or runtime.resolve() != runtime.absolute() or not runtime.is_dir()
                or runtime.resolve().is_relative_to(Path(launch['snapshot_root']).resolve())):
            raise RuntimeError('Advisory run root must be a prepared directory outside frozen inputs')
    return launch


def trigger_store(task):
    ref=os.environ.get('GC_TRIGGER_BEAD_STORE_REF') or os.environ.get('GC_BEAD_STORE_REF')
    if not ref:ref='rig:mu-core' if task.startswith('mux-') else 'city'
    if ref not in ('city','rig:mu-core'):
        raise RuntimeError('Unsupported native Core trigger store: '+ref)
    if task.startswith('mux-') and ref!='rig:mu-core' or task.startswith('mc-') and ref!='city':
        raise RuntimeError('Native trigger store differs from assigned bead prefix')
    return ref


def gc(args, **kwargs):
    city = os.environ.get('GC_CITY')
    if not city or not Path(city).is_absolute():
        raise RuntimeError('Native city identity required for assigned-bead operations')
    if args[:1]==['bd'] and trigger_store(args[2])=='rig:mu-core':
        args=['bd','--rig','mu-core',*args[1:]]
    return subprocess.check_output(['/usr/local/bin/gc', '--city', city, *args],
        cwd=city, text=True, timeout=60, **kwargs)


def entry_for(task):
    value = json.loads(gc(['bd', 'show', task, '--json']))
    return value[0] if isinstance(value, list) else value


def toml_inline(value):
    """Encode the small invocation-only trust tables using TOML literal keys."""
    if isinstance(value,dict):
        return '{ '+', '.join(json.dumps(key,ensure_ascii=False)+' = '+toml_inline(item) for key,item in value.items())+' }'
    if isinstance(value,(str,bool,int)):
        return json.dumps(value,ensure_ascii=False)
    raise ValueError('Unsupported invocation trust value')


def invocation_trust_args(directory):
    """Trust only this prepared cwd and the existing four reviewed native hooks."""
    from runtime_hooks import reviewed_hashes
    source=str(directory/'.codex/hooks.json')
    return ['-c','projects='+toml_inline({str(directory):{'trust_level':'trusted'}}),
            '-c','hooks='+toml_inline({'state':{source+':'+key:{'trusted_hash':value}
                                              for key,value in reviewed_hashes(os.environ.get('GC_CITY') or directory).items()}})]


def clean_arguments(argv, features=()):
    """GC's provider supplies CLI flags; only competency-owned flags are replaced."""
    from role_profiles import override_root
    managed = {'model', 'model_reasoning_effort', 'developer_instructions', 'agents', 'features',
               'mcp_servers', 'profiles', 'profile', 'projects', 'hooks'}
    result = []; index = 0
    while index < len(argv):
        item = argv[index]; size = 1; value = None
        if item in ('--model', '-m', '--cd', '-C', '--profile', '-p'):
            index += 2; continue
        if item.startswith(('--model=', '--cd=', '--profile=')) or (item.startswith(('-m','-C','-p')) and not item.startswith('--') and len(item) > 2):
            index += 1; continue
        if item in ('-c', '--config') and index + 1 < len(argv):
            size = 2; value = argv[index + 1]
        elif item.startswith('--config='): value = item[9:]
        elif item.startswith('-c') and len(item) > 2: value = item[2:]
        key = override_root(value) if value is not None else None
        if key in managed:
            index += size; continue
        result.extend(argv[index:index + size]); index += size
    return result


def bound_launch(task, path, expected, argv):
    launch = read_launch(path, expected)
    assignment = launch['assignment']
    store_ref=launch.get('store_ref','city')
    if store_ref!=trigger_store(task) or (launch['mode']=='implement')!=(store_ref=='rig:mu-core'):
        raise RuntimeError('Frozen launch differs from native assigned bead store')
    if assignment['model'] == 'gpt-6-astra':
        gate = launch['escalation']
        if (assignment.get('role') not in (None, 'mu_deep_reviewer') or gate.get('previous_model') != 'gpt-6.1-sol'
                or gate.get('blocker') != 'unresolved_technical' or not gate.get('discriminator') or not gate.get('evidence')):
            raise RuntimeError('Astra launch lacks the bounded Sol discriminator evidence')
    item = entry_for(task); meta = item.get('metadata', {})
    if meta.get('mu.launch_path') != path or meta.get('mu.launch_sha256') != expected:
        raise RuntimeError('Bead launch binding changed')
    if item.get('status') == 'closed':
        gc(['runtime', 'drain-ack']); return 0
    session = os.environ.get('GC_SESSION_ID')
    if not session or (item.get('assignee') and item['assignee'] != session):
        raise RuntimeError('Trigger belongs to another session or session identity is missing')
    if not item.get('assignee'):
        gc(['bd', 'update', task, '--claim'])
    claimed = entry_for(task)
    if claimed.get('assignee') != session:
        raise RuntimeError('Native claim did not bind this trigger to this session')
    if any(claimed.get('metadata', {}).get(key) != value for key,value in meta.items() if key.startswith('mu.')):
        raise RuntimeError('Task changed while claiming')
    tooling = Path(launch['tooling_root'])
    # This process was re-executed from the selected bundle: imports cannot fall
    # back to a later shared helper deployment or the canonical Windows source.
    from role_profiles import load_profile, configuration_args
    from language_policy import WORKER_INSTRUCTIONS
    from resource_guard import run
    role = assignment.get('role')
    if role:
        profile = load_profile(role, tooling)
        if profile['profile_sha256'] != assignment['profile_sha256']:
            raise RuntimeError('Selected role differs from frozen assignment')
    else:
        profile = {'model': assignment['model'], 'effort': assignment['effort'],
                   'features': {}, 'developer_instructions': ''}
    directory = Path.cwd().resolve() if launch['mode'] == 'implement' else tooling
    verified(directory/'.codex/hooks.json',launch['native_hooks_sha256'])
    runtime = directory / '.local/workspace' if launch['mode'] == 'implement' else Path(launch['run_root'])
    transient = directory / '.local/host/transient' if launch['mode'] == 'implement' else runtime / 'transient'
    common = ''
    if launch['mode'] == 'implement':
        marker = json.loads((directory / '.local/workspace/worker.json').read_text())
        if Path(marker['repo']).resolve() != directory or marker['base'] != launch['source_head']:
            raise RuntimeError('Prepared worker source/root differs from assignment')
        from worker_context import setup
        context = json.loads((directory / '.local/workspace/context.json').read_text())
        setup(directory, marker['base'], marker['queue_origin'], Path(context['analysis_tools']))
        config = __import__('tomllib').loads((directory / '.codex/config.toml').read_text())
        common = config.get('developer_instructions', '')
    else:
        config = __import__('tomllib').loads((tooling / '.codex/config.toml').read_text())
        common = config.get('developer_instructions', '')
    role_guidance = profile['developer_instructions']
    for prefix in ('.agents/', 'docs/', '.local/workspace/'):
        reader = directory if prefix == '.local/workspace/' else tooling
        role_guidance = role_guidance.replace(prefix, str(reader) + '/' + prefix)
    guidance = (WORKER_INSTRUCTIONS + '\n' + common + '\n' + role_guidance +
        '\nExecute ONLY Gas City bead ' + task + '. It is already claimed for this session. '
        'Native Beads store: '+store_ref+'. '+
        ('Use gc bd --rig mu-core for every operation on this task. ' if store_ref=='rig:mu-core' else '')+
        'Never claim, select or close any other bead. No nested agents. Read only assigned inputs; '
        'honor the exact write set. Save your result on this bead, close it, then immediately '
        'gc runtime drain-ack. Closing a bead does not accept parent work.\n'
        'Frozen profile/skills/CODEX_PACK root: ' + str(tooling) + '\n' + launch['body'])
    profile = {**profile, 'developer_instructions': guidance}
    from worker_context import scoped_mcp_args
    options = ['-C', str(directory), *invocation_trust_args(directory),
               *scoped_mcp_args(config), *configuration_args(profile)]
    receipt = runtime / ('launch-' + task + '.json')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({'task': task, 'session': session, 'cwd': str(directory),
        'role': role, 'store_ref':store_ref, 'profile_sha256': assignment.get('profile_sha256'), 'launch_sha256': expected,
        'tooling_root': str(tooling), 'run_root':str(runtime), 'model': profile['model'], 'effort': profile['effort'],
        'scoped_mcp_sha256':sha(json.dumps(config.get('mcp_servers',{}),sort_keys=True).encode('utf-8'))}) + '\n')
    def execute(pass_fds=()):
        return run(['codex', *options, *clean_arguments(argv, profile['features'])], cwd=directory, timeout=None,
                   transient=transient, pass_fds=pass_fds).returncode
    # Native pool capacity is the first gate. Keep the existing one-Astra rule
    # through process exit, including after the bead has closed.
    if profile['model'] == 'gpt-6-astra':
        import fcntl
        with (Path(os.environ['GC_CITY']) / '.gc/mu-deep.lock').open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = execute((handle.fileno(),))
    else:
        result = execute()
    if entry_for(task).get('status') == 'closed':
        gc(['runtime', 'drain-ack'])
    return result


def native_session():
    """Session beads are city-scoped even when their trigger belongs to a rig."""
    city=os.environ.get('GC_CITY');identity=os.environ.get('GC_SESSION_ID')
    if not city or not Path(city).is_absolute() or not identity:
        raise RuntimeError('Native session identity required before resolving a trigger')
    value=json.loads(subprocess.check_output(['/usr/local/bin/gc','--city',city,
        'bd','show',identity,'--json'],cwd=city,text=True,timeout=60))
    item=value[0] if isinstance(value,list) else value
    if item.get('id')!=identity or item.get('issue_type')!='session' or item.get('status')=='closed':
        raise RuntimeError('Native session identity is missing, closed or not a session')
    return item


def launch(argv, legacy_record=None, legacy_sha=None):
    task = os.environ.get('GC_TRIGGER_BEAD_ID') or os.environ.get('GC_BEAD_ID')
    session=None
    if not task:
        if not os.environ.get('GC_SESSION_ID'):
            raise RuntimeError('Native task trigger required before launching a model')
        session=native_session();metadata=session.get('metadata',{})
        task=metadata.get('gc.trigger_bead_id')
        if task:
            store=metadata.get('gc.trigger_bead_store_ref')
            if store not in ('city','rig:mu-core'):raise RuntimeError('Native stored trigger has no exact bead store')
            os.environ['GC_TRIGGER_BEAD_ID']=task
            os.environ['GC_TRIGGER_BEAD_STORE_REF']=store
    item=entry_for(task) if task else None
    meta=item.get('metadata',{}) if item else {}
    path=meta.get('mu.launch_path');expected=meta.get('mu.launch_sha256')
    if path and expected:
        frozen = read_launch(path, expected)
        helper = Path(frozen['tooling_root']) / '.agents/scripts/role_bootstrap.py'
        # Exec the selected helper bytes, including on resume, before importing
        # any job-specific dependencies. Existing bound jobs retain their bundle.
        os.execv(sys.executable,[sys.executable,str(helper),'--bound',task,path,expected,*argv])
        return
    if any(key.startswith('mu.launch_') or key in ('mu.role','mu.profile_sha256') for key in meta):
        raise RuntimeError('Task has incomplete immutable launch binding')
    if not legacy_record or not legacy_sha:
        raise RuntimeError('Task lacks immutable launch inputs or retained legacy identity')
    retained=json.loads(verified(legacy_record,legacy_sha))
    city=os.environ.get('GC_CITY')
    if retained.get('namespace',{}).get('city')!=city:
        raise RuntimeError('Legacy record belongs to another native city')
    session=session or native_session()
    if task:
        allowed=task in retained.get('tasks',{}).get(trigger_store(task),[])
        metadata=session.get('metadata',{})
        if metadata.get('gc.trigger_bead_id') not in (None,'',task):
            raise RuntimeError('Legacy task differs from native session trigger')
        if item.get('assignee') not in (None,'',session['id']):
            raise RuntimeError('Legacy task belongs to another session')
    else:
        allowed=session['id'] in retained.get('sessions',[])
    if not allowed:raise RuntimeError('New unbound native work cannot use legacy execution')
    if item and item.get('status')=='closed':
        gc(['runtime','drain-ack']);return
    # Preserve the original generic native path, argv and cwd. No competency
    # profile, immutable-history claim, permission change or task mutation.
    print('Retained legacy native Codex invocation; no named-role binding.',file=sys.stderr)
    os.execvp('codex',['codex',*argv])


if __name__ == '__main__':
    try:
        if sys.argv[1:2] == ['--bound']:
            raise SystemExit(bound_launch(*sys.argv[2:5], sys.argv[5:]))
        import argparse
        parser=argparse.ArgumentParser(add_help=False)
        parser.add_argument('--legacy-record')
        parser.add_argument('--legacy-sha')
        legacy,arguments=parser.parse_known_args(sys.argv[1:])
        launch(arguments,legacy.legacy_record,legacy.legacy_sha)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
