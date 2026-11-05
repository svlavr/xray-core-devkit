#!/usr/bin/env python3
"""Bind one native Gas City trigger to its immutable competency before Codex starts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import shutil
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


def invocation_trust_args(directory,city=None):
    """Trust only this prepared cwd and the existing four reviewed native hooks."""
    from runtime_hooks import reviewed_hashes,reviewed_source
    if city is not None:reviewed_source(directory,city)
    selected_city=city if city is not None else os.environ.get("GC_CITY") or directory
    source=str(directory/'.codex/hooks.json')
    return ['-c','projects='+toml_inline({str(directory):{'trust_level':'trusted'}}),
            '-c','hooks='+toml_inline({'state':{source+':'+key:{'trusted_hash':value}
                                              for key,value in reviewed_hashes(selected_city).items()}})]


def clean_arguments(argv, features=(),neutral_source=False):
    """GC's provider supplies CLI flags; only competency-owned flags are replaced."""
    from role_profiles import override_root
    managed = {'model', 'model_reasoning_effort', 'developer_instructions', 'agents', 'features',
               'mcp_servers', 'profiles', 'profile', 'projects', 'hooks'}
    result = []; index = 0
    while index < len(argv):
        item = argv[index]; size = 1; value = None
        if neutral_source and item=='--':
            result.extend(argv[index:]);break
        if item=='--dangerously-bypass-hook-trust' or item.startswith('--dangerously-bypass-hook-trust='):
            index+=1;continue
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


def configuration_globals(argv):
    """Keep final CLI discovery/configuration overrides without prompt text."""
    result=[];index=0
    while index<len(argv):
        item=argv[index]
        if item=='--':break
        if item in ('-C','--cd','-c','--config','--enable','--disable','--add-dir','-s','--sandbox','-a','--ask-for-approval'):
            if index+1>=len(argv):raise RuntimeError('Missing native configuration argument: '+item)
            result.extend(argv[index:index+2]);index+=2;continue
        if item.startswith(('--cd=','--config=','--enable=','--disable=','--add-dir=','--sandbox=','--ask-for-approval=')) or (item.startswith(('-C','-c','-s','-a')) and not item.startswith('--') and len(item)>2):
            result.append(item)
        elif item in ('--dangerously-bypass-approvals-and-sandbox','--full-auto'):
            result.append(item)
        elif item.startswith(('--config','--profile','--dangerously-bypass-hook-trust')) or item=='-p':
            raise RuntimeError('Unsupported native configuration argument: '+item)
        index+=1
    return result


def split_configuration_overrides(argv):
    """Place parent global config before the final managed override and prompt."""
    overrides=[];tail=[];index=0
    while index<len(argv):
        item=argv[index]
        if item=='--':tail.extend(argv[index:]);break
        if item in ('-c','--config'):
            if index+1>=len(argv):raise RuntimeError('Missing native configuration argument: '+item)
            overrides.extend(argv[index:index+2]);index+=2;continue
        if item.startswith('--config=') or (item.startswith('-c') and not item.startswith('--') and len(item)>2):
            overrides.append(item)
        else:tail.append(item)
        index+=1
    return overrides,tail


def source_workspace_roots(parent_roots,source_root):
    """Preserve native-normalized parent roots; add only the validated source."""
    if not isinstance(parent_roots,list):raise RuntimeError('Native workspace-write roots must be a list')
    result=[]
    for value in [*parent_roots,str(source_root)]:
        if not isinstance(value,str) or not Path(value).is_absolute():
            raise RuntimeError('Native workspace-write roots must be normalized absolute paths')
        if value not in result:result.append(value)
    return result


def validate_neutral_root(directory,git_executable):
    if not directory.is_absolute() or directory.resolve()!=directory.absolute() or not directory.is_dir():
        raise RuntimeError('Neutral tooling root must be an existing unaliased directory')
    discovery={'GIT_DIR','GIT_COMMON_DIR','GIT_WORK_TREE','GIT_CEILING_DIRECTORIES','GIT_DISCOVERY_ACROSS_FILESYSTEM'}
    if any(key in discovery or key.startswith('GIT_CONFIG') for key in os.environ):
        raise RuntimeError('Git discovery/configuration environment overrides are forbidden for neutral launch')
    if any((parent/'.git').exists() or (parent/'.git').is_symlink() for parent in (directory,*directory.parents)):
        raise RuntimeError('Neutral tooling root has Git ancestry')
    result=subprocess.run([str(git_executable),'--no-pager','--no-optional-locks','-c','core.fsmonitor=false',
        '-c','gc.auto=0','-c','maintenance.auto=false','-C',str(directory),'rev-parse','--show-toplevel'],
        capture_output=True,text=True,encoding='utf-8',timeout=10,
        env={**os.environ,'LC_ALL':'C','LANG':'C','GIT_OPTIONAL_LOCKS':'0'})
    if result.returncode!=128 or not result.stderr.startswith('fatal: not a git repository'):
        raise RuntimeError('Cannot establish absence of Git ancestry for neutral tooling root')
    return {'root':str(directory),'git_ancestry':'none','git_probe_returncode':128}


def bound_launch(task, path, expected, argv):
    launch = read_launch(path, expected)
    city=launch.get('city')
    if city is not None:
        from runtime_hooks import reviewed_document
        reviewed_document(city)
        if os.environ.get('GC_CITY')!=city:raise RuntimeError('Frozen launch city differs from native trigger city')
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
    from role_profiles import select_profile, configuration_args
    from language_policy import WORKER_INSTRUCTIONS
    from resource_guard import run
    role = assignment.get('role')
    if role:
        request=assignment.get('selection_request',{})
        if assignment.get('preset') and request.get('kind')!=launch['mode']:
            raise RuntimeError('Preset request kind differs from frozen launch mode')
        profile = select_profile(role,tooling,task=request)
        if profile['profile_sha256'] != assignment['profile_sha256']:
            raise RuntimeError('Selected role differs from frozen assignment')
        for key in ('model','effort','preset','preset_policy_path','preset_policy_sha256','preset_sha256','model_policy_sha256','selection_sha256'):
            if profile.get(key)!=assignment.get(key):raise RuntimeError('Selected model/preset identity differs from frozen assignment: '+key)
    else:
        profile = {'model': assignment['model'], 'effort': assignment['effort'],
                   'features': {}, 'developer_instructions': ''}
    source_root=Path.cwd().resolve() if launch['mode']=='implement' else None
    neutral_implementation=source_root is not None and city is not None
    directory=tooling if neutral_implementation or source_root is None else source_root
    if not neutral_implementation:
        verified(directory/'.codex/hooks.json',launch['native_hooks_sha256'])
    runtime = source_root / '.local/workspace' if source_root is not None else Path(launch['run_root'])
    transient = source_root / '.local/host/transient' if source_root is not None else runtime / 'transient'
    common = ''
    if launch['mode'] == 'implement':
        marker = json.loads((source_root / '.local/workspace/worker.json').read_text())
        if Path(marker['repo']).resolve() != source_root or marker['base'] != launch['source_head']:
            raise RuntimeError('Prepared worker source/root differs from assignment')
        from worker_context import setup
        context = json.loads((source_root / '.local/workspace/context.json').read_text())
        setup_result=setup(source_root, marker['base'], marker['queue_origin'], Path(context['analysis_tools']))
        if neutral_implementation:
            context = json.loads((source_root / '.local/workspace/context.json').read_text())
            neutral_validation=validate_neutral_root(directory,context['git_executable'])
            verified(directory/'.codex/hooks.json',launch['native_hooks_sha256'])
            source_validation={'root':str(source_root),'base':marker['base'],'queue_origin':marker['queue_origin'],
                               'worker_context':setup_result,'neutral_root':neutral_validation}
        config = __import__('tomllib').loads((source_root / '.codex/config.toml').read_text())
        common = config.get('developer_instructions', '')
    else:
        config = __import__('tomllib').loads((tooling / '.codex/config.toml').read_text())
        common = config.get('developer_instructions', '')
    role_guidance = profile['developer_instructions']
    for prefix in ('.agents/', 'docs/', '.local/workspace/'):
        reader = (source_root or directory) if prefix == '.local/workspace/' else tooling
        role_guidance = role_guidance.replace(prefix, str(reader) + '/' + prefix)
    source_guidance=''
    if neutral_implementation:
        common=common.replace('.local/workspace/',str(source_root)+'/.local/workspace/').replace('.local/host/',str(source_root)+'/.local/host/')
        source_guidance=('\nSource checkout (source_root): '+str(source_root)+'. Native Codex cwd is frozen tooling: '+str(directory)+'. '
            'Before source work, read '+str(source_root)+'/AGENTS.override.md and '+str(source_root)+'/AGENTS.md if present, plus applicable ancestor instructions. '
            'For EVERY source filesystem, shell, Git, build or test command set its workdir explicitly to this exact source_root and use absolute source paths. '
            'Never rely on the native cwd for source files. Frozen tooling is read-only reference input; never edit it. '
            'Go MCP remains bound to source_root. Runtime and temporary files remain in source_root/.local; honor the task write set.\n')
    guidance = (WORKER_INSTRUCTIONS + '\n' + common + '\n' + role_guidance + source_guidance+
        '\nExecute ONLY Gas City bead ' + task + '. It is already claimed for this session. '
        'Native Beads store: '+store_ref+'. '+
        ('Use gc bd --rig mu-core for every operation on this task. ' if store_ref=='rig:mu-core' else '')+
        'Never claim, select or close any other bead. No nested agents. Read only assigned inputs; '
        'honor the exact write set. Save your result on this bead, close it, then immediately '
        'gc runtime drain-ack. Closing a bead does not accept parent work.\n'
        'Frozen profile/skills/CODEX_PACK root: ' + str(tooling) + '\n' + launch['body'])
    profile = {**profile, 'developer_instructions': guidance}
    from worker_context import scoped_mcp_args
    options = ['-C', str(directory), *invocation_trust_args(directory,city),
               *scoped_mcp_args(config), *configuration_args(profile)]
    tail=clean_arguments(argv,profile['features'],neutral_source=neutral_implementation)
    codex='codex'
    if neutral_implementation:
        codex=shutil.which('codex')
        if not codex:raise RuntimeError('Codex executable unavailable for native hook preflight')
        from runtime_hooks import verify_invocation_hooks
        parent_config,tail=split_configuration_overrides(tail)
        options.extend(parent_config)
        parent_validation=verify_invocation_hooks(directory,city,configuration_globals([*options,*tail]),
            expected_sha256=launch['native_hooks_sha256'],transient=transient,codex=codex,read_workspace_roots=True)
        parent_roots=parent_validation['workspace_write_roots']
        workspace_roots=source_workspace_roots(parent_roots,source_root)
        options.extend(['-c','sandbox_workspace_write.writable_roots='+json.dumps(workspace_roots)])
        hook_validation=verify_invocation_hooks(directory,city,configuration_globals([*options,*tail]),
            expected_sha256=launch['native_hooks_sha256'],transient=transient,codex=codex,read_workspace_roots=True)
        if hook_validation['workspace_write_roots']!=workspace_roots:
            raise RuntimeError('Native final workspace-write roots differ from the preserved source binding')
        source_validation['workspace_write_roots']={'parent':parent_roots,'invocation':workspace_roots,
            'relative_cli_root_anchor':str(directory),'scope':'Legacy workspace-write field only; parent mode and modern permission profiles remain authoritative'}
    receipt = runtime / ('launch-' + task + '.json')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({'task': task, 'session': session, 'cwd': str(directory),
        'role': role, 'store_ref':store_ref, 'profile_sha256': assignment.get('profile_sha256'), 'launch_sha256': expected,
        **({key:profile[key] for key in ('preset','preset_policy_sha256','preset_sha256','model_policy_sha256','selection_sha256')} if profile.get('preset') else {}),
        'tooling_root': str(tooling), 'run_root':str(runtime), 'model': profile['model'], 'effort': profile['effort'],
        'scoped_mcp_sha256':sha(json.dumps(config.get('mcp_servers',{}),sort_keys=True).encode('utf-8')),
        **({'source_root':str(source_root),'source_validation':source_validation,'native_hook_validation':hook_validation}
           if neutral_implementation else {})}) + '\n')
    def execute(pass_fds=()):
        return run([codex, *options, *tail], cwd=directory, timeout=None,
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
