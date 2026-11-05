"""Exercise native launch construction without model, Git mutation or auth calls."""
import copy
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import agent_batch as batch
import resource_guard
import role_bootstrap as bootstrap
import role_profiles
import worker_context
import runtime_hooks


class LaunchTests(unittest.TestCase):
    def test_native_trigger_store_scopes_bootstrap_show_claim_and_preserves_city_resume(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'GC_CITY':folder,
                'GC_TRIGGER_BEAD_STORE_REF':'rig:mu-core'}), \
             patch.object(bootstrap.subprocess,'check_output',return_value='[{}]') as invoke:
            bootstrap.entry_for('mux-task')
            bootstrap.gc(['bd','update','mux-task','--claim'])
            commands=[call.args[0] for call in invoke.call_args_list]
            self.assertEqual(commands[0],['/usr/local/bin/gc','--city',folder,'bd','--rig','mu-core','show','mux-task','--json'])
            self.assertEqual(commands[1],['/usr/local/bin/gc','--city',folder,'bd','--rig','mu-core','update','mux-task','--claim'])
            with self.assertRaisesRegex(RuntimeError,'differs from assigned bead prefix'):bootstrap.entry_for('mc-adviser')
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(bootstrap.trigger_store('mux-task'),'rig:mu-core')
            self.assertEqual(bootstrap.trigger_store('mc-adviser'),'city')
        with tempfile.TemporaryDirectory() as folder:
            _,_,_,bindings,_=self.fixture(Path(folder));binding=bindings['one']
            path=Path(binding['path']);launch=json.loads(path.read_bytes());launch.pop('store_ref')
            path.write_bytes(batch.encoded(launch));binding={**binding,'sha256':batch.digest(path.read_bytes())}
            result,run,_=self.execute('mc-old-bound-adviser',binding,['resume','key'])
            self.assertEqual(result,0);run.assert_called_once()

    def test_invocation_trust_has_exact_owned_root_and_four_existing_native_hook_keys(self):
        directory=Path('/prepared/exact-root')
        with patch.dict(os.environ,{'GC_CITY':'/fixture/city'}):args=bootstrap.invocation_trust_args(directory)
        self.assertTrue(args[1].startswith('projects={ '));self.assertTrue(args[3].startswith('hooks={ '))
        config=tomllib.loads('\n'.join(args[index+1] for index,item in enumerate(args) if item=='-c'))
        self.assertEqual(config['projects'],{str(directory):{'trust_level':'trusted'}})
        source=str(directory/'.codex/hooks.json')
        self.assertEqual(config['hooks']['state'],{source+':'+key:{'trusted_hash':value}
            for key,value in runtime_hooks.reviewed_hashes('/fixture/city').items()})
        for key in ('sandbox_mode','approval_policy','model_provider'):self.assertNotIn(key,config)

    def test_bound_root_and_competency_win_without_changing_permission_flags(self):
        self.assertEqual(bootstrap.clean_arguments(['--dangerously-bypass-hook-trust','resume','--dangerously-bypass-hook-trust=true','session']),['resume','session'])
        inherited=['--dangerously-bypass-approvals-and-sandbox','--sandbox','workspace-write']
        args=['resume','session','--cd','/stale','-C/stale','--model=stale',
              '-c','model="stale"','-c','features.shell_tool=true',*inherited]
        self.assertEqual(bootstrap.clean_arguments(args,['shell_tool']),['resume','session',*inherited])

    def test_quoted_dotted_reserved_overrides_and_profile_aliases_cannot_replace_binding(self):
        for value in ('"model"="stale"', "'developer_instructions'=stale", '"agents".enabled=true',
                      "'mcp_servers'.wrong.command=stale", '"features".shell_tool=true',
                      'profiles.untrusted.model=stale','projects.wrong.trust_level=trusted',
                      'hooks.state.wrong.trusted_hash=wrong'):
            for option in (['-c',value],['--config='+value],['-c'+value]):
                self.assertEqual(bootstrap.clean_arguments(['resume','key',*option]),['resume','key'])
        for option in (['--profile','stale'],['-p','stale'],['--profile=stale'],['-pstale']):
            self.assertEqual(bootstrap.clean_arguments([*option,'resume','key']),['resume','key'])
        self.assertEqual(bootstrap.clean_arguments(['-c','model_context_window=872000']),['-c','model_context_window=872000'])

    def fixture(self, root,city=None):
        source=root/'source';source.mkdir()
        files={
            'go.mod':b'module github.com/xtls/xray-core\n',
            '.agents/orchestration/models.json':(batch.ROOT/'.agents/orchestration/models.json').read_bytes(),
            '.agents/CODEX_PACK.md':b'Common English worker guidance',
            '.agents/skills/xray-test/SKILL.md':b'Read references/selected.md',
            '.agents/skills/xray-test/references/selected.md':b'Selected skill reference',
        }
        for name in ('role_bootstrap.py','role_profiles.py','resource_guard.py','worker_context.py','go_mcp.py','language_policy.py','runtime_hooks.py'):
            files['.agents/scripts/'+name]=Path(__file__).with_name(name).read_bytes()
        for role,label in [('mu_innovator','INNOVATOR TEST COMPETENCY'),('mu_security_reviewer','SECURITY TEST COMPETENCY')]:
            files['.codex/agents/'+role+'.toml']=(f'name = "{role}"\ndescription = "fixture"\nmodel = "gpt-6.1-sol"\n'
                'model_reasoning_effort = "high"\nsandbox_mode = "read-only"\n'
                f'developer_instructions = "{label}. Read .agents/CODEX_PACK.md and .agents/skills/xray-test/SKILL.md"\n'
                '[agents]\nenabled = false\n').encode()
        for name,raw in files.items():
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        target=root/'frozen';target.mkdir()
        tasks=[{'key':key,'kind':'review','role':role,'title':key,'body':'Inspect supplied inputs only.',
                'inputs':['current']} for key,role in [('one','mu_innovator'),('two','mu_security_reviewer')]]
        run_root=root/'runs'
        for task in tasks:(run_root/task['key']/'transient').mkdir(parents=True)
        native_hooks=b'{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"fixture native hook"}]}]}}'
        if city is not None:native_hooks=json.dumps(runtime_hooks.reviewed_document(city)).encode()
        launches,manifest=batch.freeze_launches(target,target.as_posix(),tasks,'a'*40,lambda task:['/frozen-source/current'],source,
            run_root=run_root.as_posix(),run_directory=run_root,native_hooks=native_hooks,city=city)
        return source,target,tasks,launches,manifest

    def execute(self, task, binding, argv=(), runner=None, store_ref='city',city=None):
        item={'id':task,'status':'open','assignee':None,'metadata':{
            'mu.launch_path':binding['path'],'mu.launch_sha256':binding['sha256'],'mu.task_hash':'task-hash'}}
        calls=[]
        def gc(args,**kwargs):
            calls.append(args)
            if args[:2]==['bd','update']:item['assignee']='session-one'
            return '{}'
        with patch.object(bootstrap,'entry_for',side_effect=lambda key:copy.deepcopy(item)), \
             patch.object(bootstrap,'gc',side_effect=gc), \
             patch.object(resource_guard,'run',side_effect=runner,return_value=subprocess.CompletedProcess([],0)) as run, \
             patch.dict(os.environ,{'GC_SESSION_ID':'session-one','GC_TRIGGER_BEAD_STORE_REF':store_ref,'GC_CITY':city or '/fixture/city'}):
            result=bootstrap.bound_launch(task,binding['path'],binding['sha256'],list(argv))
        return result,run,calls

    def test_read_only_snapshot_uses_only_prepared_separate_run_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,target,_,bindings,manifest=self.fixture(root)
            binding=bindings['one'];launch=json.loads(Path(binding['path']).read_bytes())
            runtime=Path(launch['run_root'])
            self.assertTrue(runtime.is_dir());self.assertFalse(runtime.is_relative_to(target))
            original_mkdir=Path.mkdir;original_write=Path.write_text;original_bytes=Path.write_bytes
            def reject_frozen(function):
                def guarded(path,*args,**kwargs):
                    if path.resolve().is_relative_to(target.resolve()):raise PermissionError('read-only snapshot')
                    return function(path,*args,**kwargs)
                return guarded
            def runner(command,**kwargs):
                self.assertEqual(kwargs['cwd'],target/'tooling/one')
                self.assertEqual(kwargs['transient'],runtime/'transient')
                (kwargs['transient']/'execution-control').write_text('stub executed', encoding='utf-8')
                return subprocess.CompletedProcess(command,0)
            paths=list(target.rglob('*'))
            try:
                for path in paths:path.chmod(0o555 if path.is_dir() else 0o444)
                target.chmod(0o555)
                if os.name=='posix' and os.geteuid()!=0:
                    with self.assertRaises(PermissionError):(target/'forbidden-control').write_text('must fail', encoding='utf-8')
                with patch.object(Path,'mkdir',reject_frozen(original_mkdir)), \
                     patch.object(Path,'write_text',reject_frozen(original_write)), \
                     patch.object(Path,'write_bytes',reject_frozen(original_bytes)):
                    result,run,_=self.execute('readonly-adviser',binding,runner=runner)
                self.assertEqual(result,0);run.assert_called_once()
                self.assertTrue((runtime/'launch-readonly-adviser.json').is_file())
                self.assertEqual((runtime/'transient/execution-control').read_text(encoding='utf-8'),'stub executed')
                batch.verify_copy(target,manifest)
                self.assertFalse((target/'tooling/one/.local/workspace/launch-readonly-adviser.json').exists())
            finally:
                target.chmod(0o755)
                for path in paths:path.chmod(0o755 if path.is_dir() else 0o644)

    def test_two_roles_in_one_pool_bind_independent_developer_profiles_before_run(self):
        with tempfile.TemporaryDirectory() as folder:
            source,target,tasks,bindings,_=self.fixture(Path(folder))
            for key,label,other in [('one','INNOVATOR TEST COMPETENCY','SECURITY TEST COMPETENCY'),
                                    ('two','SECURITY TEST COMPETENCY','INNOVATOR TEST COMPETENCY')]:
                result,run,calls=self.execute('task-'+key,bindings[key],['resume','session-key','-c','developer_instructions="stale"'])
                self.assertEqual(result,0);self.assertEqual(calls,[['bd','update','task-'+key,'--claim']])
                command=run.call_args.args[0]
                settings={command[i+1].split('=',1)[0]:command[i+1].split('=',1)[1]
                    for i,arg in enumerate(command) if arg=='-c'}
                self.assertIn(label,settings['developer_instructions']);self.assertNotIn(other,settings['developer_instructions'])
                self.assertNotIn('stale',settings['developer_instructions'])
                self.assertIn('never send private source',settings['developer_instructions'])
                self.assertEqual(settings['model'],'"gpt-6.1-sol"');self.assertEqual(settings['agents.enabled'],'false')
                self.assertIn('resume',command);self.assertEqual(command[-2:],['resume','session-key'])
                self.assertNotIn('sandbox_mode',settings);self.assertNotIn('approval_policy',settings)
                explicit='\n'.join(command[index+1] for index,item in enumerate(command) if item=='-c')
                mcp=tomllib.loads(explicit)['mcp_servers']
                self.assertEqual(mcp['context7']['url'],'https://mcp.context7.com/mcp')
                self.assertEqual(mcp['grep_app']['enabled_tools'],['searchGitHub'])
                self.assertNotIn('xray_gopls_worker',mcp)
                self.assertEqual(tomllib.loads(explicit)['projects'],{str(target/'tooling'/key):{'trust_level':'trusted'}})
                self.assertEqual(len(tomllib.loads(explicit)['hooks']['state']),4)
                self.assertTrue((target/'tooling'/key/'.agents/skills/xray-test/references/selected.md').is_file())

    def test_source_changes_do_not_rewrite_active_frozen_profile_or_helpers(self):
        with tempfile.TemporaryDirectory() as folder:
            source,target,tasks,bindings,_=self.fixture(Path(folder))
            profile=source/'.codex/agents/mu_innovator.toml'
            profile.write_text(profile.read_text(encoding='utf-8').replace('INNOVATOR TEST COMPETENCY','LATER PROFILE'), encoding='utf-8')
            (source/'.agents/scripts/role_bootstrap.py').write_text('raise RuntimeError("later helper")', encoding='utf-8')
            _,run,_=self.execute('retained',bindings['one'])
            self.assertIn('INNOVATOR TEST COMPETENCY',' '.join(run.call_args.args[0]))
            item={'metadata':{'mu.launch_path':bindings['one']['path'],'mu.launch_sha256':bindings['one']['sha256']}}
            with patch.object(bootstrap,'entry_for',return_value=item),patch.object(os,'execv') as execute, \
                 patch.dict(os.environ,{'GC_TRIGGER_BEAD_ID':'retained'}):bootstrap.launch(['resume','session'])
            self.assertEqual(execute.call_args.args[1][1],str(target/'tooling/one/.agents/scripts/role_bootstrap.py'))

    def test_implementation_actual_command_receives_frozen_mcp_adapter_and_bound_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,target,_,bindings,_=self.fixture(root);binding=bindings['one']
            path=Path(binding['path']);launch=json.loads(path.read_bytes());launch['mode']='implement'
            launch['store_ref']='rig:mu-core'
            path.write_bytes(batch.encoded(launch));binding={**binding,'sha256':batch.digest(path.read_bytes())}
            worker=root/'worker';local=worker/'.local/workspace';local.mkdir(parents=True)
            (worker/'.codex').mkdir()
            (worker/'.codex/hooks.json').write_bytes((target/'tooling/one/.codex/hooks.json').read_bytes())
            (local/'worker.json').write_text(json.dumps({'repo':str(worker),'base':'a'*40,'queue_origin':'/local/queue'}), encoding='utf-8')
            (local/'context.json').write_text(json.dumps({'analysis_tools':'/tools'}), encoding='utf-8')
            adapter=target/'tooling/one/.agents/scripts/go_mcp.py'
            config={'developer_instructions':'Prepared worker queue guidance.',
                'mcp_servers':{'xray_gopls_worker':{'enabled':True,'command':'/usr/bin/python3',
                    'args':[str(adapter),'--binary','/tools/gopls','--root',str(worker)]}}}
            def setup(*args):
                directory=worker/'.codex';directory.mkdir(exist_ok=True)
                # JSON inline tables are not TOML, so emit the normal explicit layer.
                settings=worker_context.scoped_mcp_args(config)
                text='developer_instructions = "Prepared worker queue guidance."\n'
                text+='\n'.join(settings[index+1] for index,item in enumerate(settings) if item=='-c')
                (directory/'config.toml').write_text(text, encoding='utf-8')
            with patch.object(bootstrap.Path,'cwd',return_value=worker),patch.object(worker_context,'setup',side_effect=setup) as provision:
                _,run,_=self.execute('mux-implementation',binding,['-c','"mcp_servers".wrong.command=stale'],store_ref='rig:mu-core')
            provision.assert_called_once_with(worker,'a'*40,'/local/queue',Path('/tools'))
            command=run.call_args.args[0]
            effective=tomllib.loads('\n'.join(command[index+1] for index,item in enumerate(command) if item=='-c'))
            self.assertEqual(effective['mcp_servers'],config['mcp_servers'])
            self.assertIn('Prepared worker queue guidance.',effective['developer_instructions'])
            self.assertEqual(command[:3],['codex','-C',str(worker)])
            self.assertEqual(run.call_args.kwargs['cwd'],worker)

    def test_tampered_profile_or_helper_refuses_before_claim_and_model(self):
        for relative in ('.codex/agents/mu_innovator.toml','.agents/scripts/resource_guard.py','.codex/hooks.json'):
            with tempfile.TemporaryDirectory() as folder:
                _,target,_,bindings,_=self.fixture(Path(folder))
                (target/'tooling/one'/relative).write_bytes(b'tampered')
                with patch.object(bootstrap,'gc') as native,patch.object(resource_guard,'run') as run:
                    with self.assertRaisesRegex(RuntimeError,'hash mismatch'):
                        bootstrap.bound_launch('one',bindings['one']['path'],bindings['one']['sha256'],[])
                    native.assert_not_called();run.assert_not_called()

    def test_missing_trigger_wrong_claim_and_closed_task_never_launch_model(self):
        with patch.dict(os.environ,{},clear=True),patch.object(bootstrap,'entry_for') as show:
            with self.assertRaisesRegex(RuntimeError,'trigger required'):bootstrap.launch([])
            show.assert_not_called()
        with tempfile.TemporaryDirectory() as folder:
            _,_,_,bindings,_=self.fixture(Path(folder));binding=bindings['one']
            meta={'mu.launch_path':binding['path'],'mu.launch_sha256':binding['sha256']}
            with patch.object(bootstrap,'entry_for',return_value={'status':'closed','metadata':meta}), \
                 patch.object(bootstrap,'gc') as gc,patch.object(resource_guard,'run') as run:
                self.assertEqual(bootstrap.bound_launch('one',binding['path'],binding['sha256'],[]),0)
                gc.assert_called_once_with(['runtime','drain-ack']);run.assert_not_called()
            with patch.object(bootstrap,'entry_for',return_value={'status':'open','metadata':meta,'assignee':'other'}), \
                 patch.object(bootstrap,'gc') as gc,patch.object(resource_guard,'run') as run, \
                 patch.dict(os.environ,{'GC_SESSION_ID':'ours'}):
                with self.assertRaisesRegex(RuntimeError,'another session'):
                    bootstrap.bound_launch('one',binding['path'],binding['sha256'],[])
                gc.assert_not_called();run.assert_not_called()

    def test_all_real_catalog_profiles_have_readable_bounded_tooling_inputs(self):
        for profile in role_profiles.list_profiles(batch.ROOT):
            task={'kind':'review','role':profile['role']}
            if profile['role']=='mu_deep_reviewer':task.update(previous_model='gpt-6.1-sol',blocker='unresolved_technical',discriminator='D',evidence=['E'])
            selected,files=batch.tooling_inputs(task)
            self.assertEqual(batch.digest(files[selected['profile_path']]),selected['profile_sha256'])
            self.assertIn('.agents/CODEX_PACK.md',files)
            self.assertLess(len(files),512)

    def test_public_authority_and_non_xray_skill_packages_are_frozen(self):
        for role,skill in [('mu_critical_reviewer','adversarial-reviewer')]:
            assignment,files=batch.tooling_inputs({'kind':'review','role':role,'skills':[skill]})
            self.assertIn('docs/PROJECT_SCOPE.md',files)
            self.assertIn('docs/WORKFLOW.md',files)
            self.assertIn('.agents/skills/'+skill+'/SKILL.md',files)
            self.assertFalse(any(name.startswith('.private/') for name in files))
        _,files=batch.tooling_inputs({'kind':'review','role':'mu_investigator',
                                      'skills':['security-threat-model','handoff']})
        self.assertIn('.agents/skills/security-threat-model/references/output-contract.md',files)
        self.assertIn('.agents/skills/handoff/SKILL.md',files)

    def test_invocation_trust_preserves_unicode_toml_literal_roots(self):
        directory=Path('/prepared/worker '+chr(0x1f680))
        with patch.dict(os.environ,{'GC_CITY':'/fixture/city'}):
            args=bootstrap.invocation_trust_args(directory)
        effective=tomllib.loads('\n'.join(args[index+1] for index,item in enumerate(args) if item=='-c'))
        self.assertEqual(effective['projects'],{str(directory):{'trust_level':'trusted'}})

    def test_bound_resume_recovers_exact_native_trigger_when_env_is_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            _,target,_,bindings,_=self.fixture(Path(folder));binding=bindings['one']
            task={'metadata':{'mu.launch_path':binding['path'],'mu.launch_sha256':binding['sha256']}}
            session={'id':'old-session','issue_type':'session','status':'open','metadata':{
                'gc.trigger_bead_id':'mc-bound','gc.trigger_bead_store_ref':'city'}}
            with patch.dict(os.environ,{'GC_CITY':'/fixture/city','GC_SESSION_ID':'old-session'},clear=True), \
                 patch.object(bootstrap,'native_session',return_value=session), \
                 patch.object(bootstrap,'entry_for',return_value=task) as show,patch.object(os,'execv') as execute, \
                 patch.object(os,'execvp') as legacy:
                bootstrap.launch(['resume','vendor-session'])
                show.assert_called_once_with('mc-bound')
                self.assertEqual(os.environ['GC_TRIGGER_BEAD_STORE_REF'],'city')
                self.assertEqual(execute.call_args.args[1][1],str(target/'tooling/one/.agents/scripts/role_bootstrap.py'))
                legacy.assert_not_called()

    def test_only_retained_unbound_native_identities_keep_original_generic_invocation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'retained.json'
            raw=batch.encoded({'namespace':{'city':'/fixture/city'},'sessions':['old-manual'],
                               'tasks':{'city':['mc-old']}})
            path.write_bytes(raw)
            original=['resume','vendor-session','-c','model="old-model"']
            for identity,trigger in [('old-manual',None),('old-pool','mc-old')]:
                metadata={} if trigger is None else {'gc.trigger_bead_id':trigger,'gc.trigger_bead_store_ref':'city'}
                session={'id':identity,'issue_type':'session','status':'open','metadata':metadata}
                with patch.dict(os.environ,{'GC_CITY':'/fixture/city','GC_SESSION_ID':identity},clear=True), \
                     patch.object(bootstrap,'native_session',return_value=session), \
                     patch.object(bootstrap,'entry_for',return_value={'status':'open','metadata':{}}), \
                     patch.object(os,'execvp') as execute,patch.object(bootstrap,'gc') as native:
                    bootstrap.launch(original,str(path),batch.digest(raw))
                    execute.assert_called_once_with('codex',['codex',*original])
                    native.assert_not_called()
            session={'id':'new-session','issue_type':'session','status':'open','metadata':{}}
            with patch.dict(os.environ,{'GC_CITY':'/fixture/city','GC_SESSION_ID':'new-session'},clear=True), \
                 patch.object(bootstrap,'native_session',return_value=session),patch.object(os,'execvp') as execute:
                with self.assertRaisesRegex(RuntimeError,'New unbound'):
                    bootstrap.launch(original,str(path),batch.digest(raw))
                execute.assert_not_called()
            with patch.dict(os.environ,{'GC_CITY':'/fixture/city','GC_SESSION_ID':'old-manual','GC_TRIGGER_BEAD_ID':'mc-old'},clear=True), \
                 patch.object(bootstrap,'entry_for',return_value={'metadata':{'mu.launch_path':'/partial'}}), \
                 patch.object(os,'execvp') as execute:
                with self.assertRaisesRegex(RuntimeError,'incomplete immutable'):
                    bootstrap.launch(original,str(path),batch.digest(raw))
                execute.assert_not_called()

    def test_native_session_lookup_is_city_scoped_and_rejects_wrong_identity(self):
        item={'id':'real-session','issue_type':'session','status':'open','metadata':{}}
        city=str(Path.cwd())
        with patch.dict(os.environ,{'GC_CITY':city,'GC_SESSION_ID':'real-session',
                                   'GC_TRIGGER_BEAD_STORE_REF':'rig:mu-core'},clear=True), \
             patch.object(bootstrap.subprocess,'check_output',return_value=json.dumps([item])) as native:
            self.assertEqual(bootstrap.native_session(),item)
            self.assertEqual(native.call_args.args[0],['/usr/local/bin/gc','--city',city,'bd','show','real-session','--json'])
            item['issue_type']='task';native.return_value=json.dumps([item])
            with self.assertRaisesRegex(RuntimeError,'not a session'):bootstrap.native_session()

    def test_explicit_invalid_role_has_no_legacy_fallback(self):
        with self.assertRaises(ValueError):batch.tooling_inputs({'kind':'review','role':'not-a-role'})


    def test_new_launch_city_binds_known_template_and_exact_invocation_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            city='/srv/reviewed-city';_,target,_,bindings,_=self.fixture(Path(directory),city=city)
            launch=json.loads(Path(bindings['one']['path']).read_bytes())
            self.assertEqual(launch['city'],city)
            result,run,_=self.execute('mc-current',bindings['one'],city=city)
            self.assertEqual(result,0)
            command=run.call_args.args[0]
            overrides=[command[index+1] for index,value in enumerate(command[:-1]) if value=='-c']
            state=tomllib.loads(next(value for value in overrides if value.startswith('hooks=')))['hooks']['state']
            source=str(target/'tooling/one/.codex/hooks.json')
            self.assertEqual(state,{source+':'+key:{'trusted_hash':value} for key,value in runtime_hooks.reviewed_hashes(city).items()})
            with self.assertRaisesRegex(RuntimeError,'city differs from native trigger city'):
                self.execute('mc-current',bindings['one'],city='/srv/wrong-city')






    def outside_git_temp(self):
        base=Path(os.environ['LOCALAPPDATA'])/'Temp' if os.name=='nt' else Path('/tmp')
        folder=tempfile.TemporaryDirectory(prefix='mu-neutral-',dir=base)
        self.assertTrue(Path(folder.name).resolve().is_relative_to(base.resolve()))
        self.addCleanup(folder.cleanup)
        return Path(folder.name).resolve()

    def test_configuration_globals_keep_final_order_and_stop_at_literal_prompt(self):
        args=['-C','/neutral','-c','model="selected"','--config=hooks.state={}',
              '--disable','plugins','--enable=known','--add-dir','/source','--sandbox','read-only',
              'resume','session','--','--config','literal prompt']
        self.assertEqual(bootstrap.configuration_globals(args),args[:12])
        with self.assertRaisesRegex(RuntimeError,'Unsupported native configuration'):
            bootstrap.configuration_globals(['--config-file=/unreviewed'])
        tail=['resume','key','--add-dir','/foreign','--add-dir=/second','--sandbox','read-only','--','--add-dir','literal']
        self.assertEqual(bootstrap.clean_arguments(tail,neutral_source=True),tail)
        config,rest=bootstrap.split_configuration_overrides(['resume','key','--config','parent=1','-csecond=2','prompt','--','--config','literal'])
        self.assertEqual(config,['--config','parent=1','-csecond=2'])
        self.assertEqual(rest,['resume','key','prompt','--','--config','literal'])

    def test_workspace_roots_preserve_native_absolute_parents_without_policy_classification(self):
        root=self.outside_git_temp();parent=str(root/'existing');source=root/'source'
        self.assertEqual(bootstrap.source_workspace_roots([parent,parent,str(source)],source),[parent,str(source)])
        self.assertEqual(bootstrap.source_workspace_roots([],source),[str(source)])
        with self.assertRaisesRegex(RuntimeError,'normalized absolute'):
            bootstrap.source_workspace_roots(['relative-root'],source)

    def test_neutral_root_rejects_git_ancestry_and_environment_overrides(self):
        with self.assertRaisesRegex(RuntimeError,'Git ancestry'):
            bootstrap.validate_neutral_root(Path(__file__).resolve().parent,sys.executable)
        root=self.outside_git_temp();executable=shutil.which('git')
        self.assertIsNotNone(executable)
        self.assertEqual(bootstrap.validate_neutral_root(root,executable)['git_ancestry'],'none')
        for key in ('GIT_DIR','GIT_COMMON_DIR','GIT_WORK_TREE','GIT_CEILING_DIRECTORIES','GIT_CONFIG_COUNT'):
            with patch.dict(os.environ,{key:'override'}),self.assertRaisesRegex(RuntimeError,'environment overrides'):
                bootstrap.validate_neutral_root(root,executable)
        with patch.object(bootstrap.subprocess,'run',return_value=subprocess.CompletedProcess([],128,'','fatal: another failure')):
            with self.assertRaisesRegex(RuntimeError,'Cannot establish absence'):bootstrap.validate_neutral_root(root,executable)

    def test_new_implementation_runs_in_neutral_tooling_with_source_owned_mcp_and_scratch(self):
        root=self.outside_git_temp()
        city='/srv/core-city'
        _,target,_,bindings,_=self.fixture(root,city=city)
        path=Path(bindings['one']['path']);launch=json.loads(path.read_bytes())
        launch.update(mode='implement',store_ref='rig:mu-core')
        path.write_bytes(batch.encoded(launch));binding={**bindings['one'],'sha256':batch.digest(path.read_bytes())}
        tooling=target/'tooling/one';worker=root/'worker';local=worker/'.local/workspace';local.mkdir(parents=True)
        (worker/'.codex').mkdir();source_hooks=worker/'.codex/hooks.json';source_hooks.write_text('untrusted provider staging must stay untouched')
        (local/'worker.json').write_text(json.dumps({'repo':str(worker),'base':'a'*40,'queue_origin':'/queue'}))
        git_executable=shutil.which('git');self.assertIsNotNone(git_executable)
        (local/'context.json').write_text(json.dumps({'analysis_tools':'/tools','git_executable':git_executable}))
        config={'mcp_servers':{'worker_go':{'command':'worker-gopls','args':['--root',str(worker)]}}}
        def setup(*args):
            self.assertEqual(args,(worker,'a'*40,'/queue',Path('/tools')))
            layer=worker_context.scoped_mcp_args(config)
            (worker/'.codex/config.toml').write_text('developer_instructions="read .local/workspace/worker.json"\n'+'\n'.join(layer[i+1] for i,x in enumerate(layer) if x=='-c'))
            return {'status':'WORKER_CONFIGURED','root':str(worker)}
        with patch.object(bootstrap.Path,'cwd',return_value=worker),patch.object(worker_context,'setup',side_effect=setup), \
             patch.object(bootstrap,'validate_neutral_root',wraps=bootstrap.validate_neutral_root) as neutral, \
             patch.object(bootstrap.shutil,'which',return_value='/exact/codex'), \
             patch.object(runtime_hooks,'verify_invocation_hooks',side_effect=[{'trusted_hooks':4,'workspace_write_roots':[str(root/'parent'),str(root/'parent')]},
                 {'trusted_hooks':4,'workspace_write_roots':[str(root/'parent'),str(worker)]}]) as preflight:
            _,runner,_=self.execute('mux-city-worker',binding,['--sandbox','read-only','--config','sandbox_workspace_write.writable_roots='+json.dumps([str(root/'parent')])],store_ref='rig:mu-core',city=city)
        neutral.assert_called_once_with(tooling,git_executable)
        command=runner.call_args.args[0]
        self.assertEqual(command[:3],['/exact/codex','-C',str(tooling)])
        self.assertEqual(runner.call_args.kwargs['cwd'],tooling)
        self.assertEqual(runner.call_args.kwargs['transient'],worker/'.local/host/transient')
        self.assertFalse(any(value.startswith('--add-dir') for value in command))
        self.assertEqual(preflight.call_args.args,(tooling,city,bootstrap.configuration_globals(command[1:])))
        self.assertTrue(preflight.call_args.kwargs['read_workspace_roots'])
        self.assertEqual(preflight.call_count,2)
        self.assertEqual(preflight.call_args.kwargs['transient'],worker/'.local/host/transient')
        values=tomllib.loads('\n'.join(command[i+1] for i,x in enumerate(command[:-1]) if x=='-c'))
        self.assertEqual(values['mcp_servers'],config['mcp_servers'])
        self.assertEqual(values['sandbox_workspace_write']['writable_roots'],[str(root/'parent'),str(worker)])
        self.assertIn(str(worker)+'/AGENTS.override.md',values['developer_instructions'])
        self.assertIn('EVERY source',values['developer_instructions'])
        self.assertEqual(source_hooks.read_text(),'untrusted provider staging must stay untouched')
        receipt=json.loads((local/'launch-mux-city-worker.json').read_text())
        self.assertEqual((receipt['cwd'],receipt['source_root']),(str(tooling),str(worker)))
        self.assertEqual(receipt['source_validation']['root'],str(worker))
        self.assertEqual(receipt['source_validation']['workspace_write_roots']['relative_cli_root_anchor'],str(tooling))

    def preset_fixture(self,root,name):
        entry=role_profiles.preset_policy()[0][name]
        task={'key':'one','kind':entry['kinds'][0],'role':entry['role'],'preset':name,'bounded':True,
              'title':'Bounded preset caller','body':'Exercise only the assigned bounded acceptance.','inputs':['current']}
        source=root/'live-source';source.mkdir()
        shutil.copytree(batch.ROOT/'.agents/skills',source/'.agents/skills')
        _,inputs=batch.tooling_inputs(task)
        for relative,raw in inputs.items():
            target_file=source/relative;target_file.parent.mkdir(parents=True,exist_ok=True);target_file.write_bytes(raw)
        target=root/'frozen';target.mkdir();runtime=root/'runs';(runtime/'one/transient').mkdir(parents=True)
        bindings,manifest=batch.freeze_launches(target,target.as_posix(),[task],'a'*40,lambda task:['/frozen-source/current'],source,
            run_root=runtime.as_posix(),run_directory=runtime,native_hooks=b'legacy immutable hook fixture')
        return task,target,bindings['one'],manifest

    def test_each_preset_survives_freezing_and_bootstrap_actual_model_arguments(self):
        for name in role_profiles.preset_policy()[0]:
            with self.subTest(preset=name),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);task,target,binding,manifest=self.preset_fixture(root,name)
                launch=json.loads(Path(binding['path']).read_bytes())
                self.assertIn('.agents/orchestration/model-presets.json',launch['files'])
                self.assertEqual(launch['assignment']['preset'],name)
                self.assertEqual(launch['assignment']['model'],'gpt-6.1-terra')
                if task['kind']=='implement':
                    worker=root/'worker';local=worker/'.local/workspace';local.mkdir(parents=True);(worker/'.codex').mkdir()
                    (worker/'.codex/hooks.json').write_bytes((target/'tooling/one/.codex/hooks.json').read_bytes())
                    (local/'worker.json').write_text(json.dumps({'repo':str(worker),'base':'a'*40,'queue_origin':'/queue'}))
                    (local/'context.json').write_text(json.dumps({'analysis_tools':'/tools'}))
                    def setup(*args):
                        (worker/'.codex/config.toml').write_text('developer_instructions="worker fixture"\n')
                    with patch.object(bootstrap.Path,'cwd',return_value=worker),patch.object(worker_context,'setup',side_effect=setup):
                        result,runner,_=self.execute('mux-preset',binding,['--model','gpt-6.1-sol','-c','model_reasoning_effort="medium"'],store_ref='rig:mu-core')
                    receipt=local/'launch-mux-preset.json'
                else:
                    result,runner,_=self.execute('mc-preset',binding,['--model','gpt-6.1-sol','-c','model_reasoning_effort="medium"'])
                    receipt=Path(launch['run_root'])/'launch-mc-preset.json'
                self.assertEqual(result,0)
                command=runner.call_args.args[0]
                settings=tomllib.loads('\n'.join(command[i+1] for i,item in enumerate(command[:-1]) if item=='-c'))
                self.assertEqual((settings['model'],settings['model_reasoning_effort']),('gpt-6.1-terra','high'))
                self.assertIn(name,settings['developer_instructions'])
                self.assertIn(role_profiles.preset_policy()[0][name]['scope'],settings['developer_instructions'])
                saved=json.loads(receipt.read_text())
                self.assertEqual(saved['selection_sha256'],launch['assignment']['selection_sha256'])
                self.assertEqual(saved['preset_policy_sha256'],launch['assignment']['preset_policy_sha256'])
                self.assertNotIn('sandbox_mode',settings)

    def test_preset_assignment_or_frozen_policy_tamper_refuses_before_model(self):
        for field,value in (('model','gpt-6.1-sol'),('effort','medium'),('preset_policy_sha256','0'*64)):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as directory:
                _,_,binding,_=self.preset_fixture(Path(directory),'native-accounting-review')
                path=Path(binding['path']);launch=json.loads(path.read_bytes());launch['assignment'][field]=value
                path.write_bytes(batch.encoded(launch));binding={**binding,'sha256':batch.digest(path.read_bytes())}
                with self.assertRaisesRegex(RuntimeError,'model/preset identity'):
                    self.execute('mc-tampered',binding)
        with tempfile.TemporaryDirectory() as directory:
            _,target,binding,_=self.preset_fixture(Path(directory),'native-accounting-review')
            (target/'tooling/one/.agents/orchestration/model-presets.json').write_text('{}')
            with patch.object(resource_guard,'run') as model:
                with self.assertRaisesRegex(RuntimeError,'Launch input hash mismatch'):
                    bootstrap.bound_launch('mc-tampered',binding['path'],binding['sha256'],[])
                model.assert_not_called()

    def test_semantic_policy_tamper_with_refreshed_file_digest_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            _,target,binding,_=self.preset_fixture(Path(directory),'native-accounting-review')
            launch_path=Path(binding['path']);launch=json.loads(launch_path.read_bytes())
            relative='.agents/orchestration/model-presets.json';policy_path=target/'tooling/one'/relative
            policy=json.loads(policy_path.read_bytes());policy['presets']['native-accounting-review']['scope']+=' Changed semantic scope.'
            policy_path.write_bytes(batch.encoded(policy));raw=policy_path.read_bytes()
            launch['files'][relative].update(sha256=batch.digest(raw),bytes=len(raw))
            launch_path.write_bytes(batch.encoded(launch));binding={**binding,'sha256':batch.digest(launch_path.read_bytes())}
            with patch.object(resource_guard,'run') as model:
                with self.assertRaisesRegex(RuntimeError,'model/preset identity'):self.execute('mc-semantic-tamper',binding)
                model.assert_not_called()

    def test_live_policy_edits_do_not_replace_valid_frozen_selection_or_resume_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,target,binding,_=self.preset_fixture(root,'native-accounting-review')
            live=root/'live-source/.agents/orchestration/model-presets.json';policy=json.loads(live.read_bytes())
            policy['presets']['native-accounting-review']['scope']+=' Live later scope.';live.write_bytes(batch.encoded(policy))
            result,model,_=self.execute('mc-frozen-preset',binding)
            self.assertEqual(result,0);command=model.call_args.args[0]
            settings=tomllib.loads('\n'.join(command[i+1] for i,value in enumerate(command[:-1]) if value=='-c'))
            self.assertEqual(settings['model'],'gpt-6.1-terra');self.assertNotIn('Live later scope.',settings['developer_instructions'])
            metadata={'mu.launch_path':binding['path'],'mu.launch_sha256':binding['sha256']}
            with patch.object(bootstrap,'entry_for',return_value={'metadata':metadata}),patch.object(os,'execv') as execute, \
                 patch.dict(os.environ,{'GC_TRIGGER_BEAD_ID':'mc-frozen-preset'}):bootstrap.launch(['resume','native-session'])
            self.assertEqual(execute.call_args.args[1][1],str(target/'tooling/one/.agents/scripts/role_bootstrap.py'))
            self.assertIn('resume',execute.call_args.args[1])



if __name__=='__main__':unittest.main()
