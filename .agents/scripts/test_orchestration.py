"""Prevent runtime config updates from discarding registered workspaces."""
import tomllib
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
import agent_batch
from model_router import resolve_assignment
from test_agent_batch import FakeNative
import orchestration
import importlib.util
import tarfile
import io
import hashlib
import os
import subprocess
import workspace
from orchestration import set_field, set_agent_field, reusable_wave, boundary_report


class RuntimeConfigurationTests(unittest.TestCase):
    def host_context(self):
        return {**json.loads((orchestration.ROOT/'examples/orchestration.json').read_text()),
                'integration_root':str(orchestration.ROOT)}

    def test_dedicated_codex_config_can_be_absent_and_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory).resolve()/'.codex/config.toml'
            roots=['/srv/xray-city','/srv/xray-city/mu-core']
            orchestration.configure_trusted_projects(target,roots)
            expected={root:{'trust_level':'trusted'} for root in roots}
            self.assertEqual(tomllib.loads(target.read_text(encoding='utf-8'))['projects'],expected)
            original='model = "custom-model"\n[projects."/keep"]\ntrust_level = "untrusted"\n'
            target.write_text(original,encoding='utf-8')
            orchestration.configure_trusted_projects(target,roots)
            text=target.read_text(encoding='utf-8');parsed=tomllib.loads(text)
            self.assertTrue(text.startswith(original))
            self.assertEqual(parsed['model'],'custom-model')
            self.assertEqual(parsed['projects']['/keep']['trust_level'],'untrusted')
            self.assertEqual({root:parsed['projects'][root] for root in roots},expected)
            orchestration.configure_trusted_projects(target,roots)
            self.assertEqual(target.read_text(encoding='utf-8'),text)
            target.write_text('invalid = [',encoding='utf-8')
            with self.assertRaises(tomllib.TOMLDecodeError):
                orchestration.configure_trusted_projects(target,roots)
            self.assertEqual(target.read_text(encoding='utf-8'),'invalid = [')

    def test_prepare_defers_reload_only_for_native_stopped_controller(self):
        # GC v1.5 cmd_citystatus.go ControllerJSON and controllerStatusForCity:
        # an unregistered cold city has running=false without pid/status;
        # a live supervisor can positively report status=stopped.
        city='/srv/xray-city'
        for controller in ({'running':False},{'running':False,'mode':'supervisor'},
                           {'running':False,'mode':'supervisor','pid':123,'status':'stopped'}):
            status={'schema_version':'1','ok':True,'city_path':city,'controller':controller}
            with self.subTest(controller=controller):
                native=unittest.mock.Mock(return_value=json.dumps(status))
                self.assertEqual(orchestration.reload_prepared_city(native,city),'deferred_stopped')
                native.assert_called_once_with(['/usr/local/bin/gc','--city',city,'status','--json'])

    def test_live_reload_failure_and_unknown_controller_state_are_not_swallowed(self):
        city='/srv/xray-city'
        base={'schema_version':'1','ok':True,'city_path':city,'controller':{'running':True,'pid':123}}
        native=unittest.mock.Mock(side_effect=[json.dumps(base),RuntimeError('native reload failed')])
        with self.assertRaisesRegex(RuntimeError,'native reload failed'):
            orchestration.reload_prepared_city(native,city)
        self.assertEqual(native.call_args.args[0],['/usr/local/bin/gc','--city',city,'reload'])
        native=unittest.mock.Mock(side_effect=[json.dumps(base),'Reload applied'])
        self.assertEqual(orchestration.reload_prepared_city(native,city),'applied')
        for changes in ({'controller':{'running':False,'pid':123,'status':'unknown'}},
                        {'controller':{'running':False,'pid':123,'status':'starting'}},
                        {'controller':{'running':False,'pid':123}},
                        {'controller':{}},{'controller':{'running':'false'}},
                        {'city_path':'/other'},{'partial':True},{'ok':False},
                        {'schema_version':'future'}):
            with self.subTest(changes=changes):
                native=unittest.mock.Mock(return_value=json.dumps({**base,**changes}))
                with self.assertRaises(RuntimeError):orchestration.reload_prepared_city(native,city)
                self.assertEqual(native.call_count,1)

    def test_host_context_is_explicit_and_cannot_alias_worker_stores(self):
        data=self.host_context()
        self.assertEqual(orchestration.validate_context(data),data)
        for key,value in [('user','root'),('distribution','bad name'),('rig_root','/mnt/c/work'),
                          ('queue_origin',data['worktree_base']),('city','/srv/../other'),
                          ('http_proxy','http://user:secret@example.invalid')]:
            with self.subTest(key=key),self.assertRaises((ValueError,RuntimeError)):
                orchestration.validate_context({**data,key:value})

    def test_init_context_sets_checkout_root_and_preserves_existing_connection(self):
        data=self.host_context()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();source=root/'edited.json';target=root/'.local/workspace/orchestration.json'
            source.write_text(json.dumps(data))
            with patch.object(orchestration,'ROOT',root),patch.object(workspace,'ROOT',root):
                result=orchestration.init_context(source)
                self.assertFalse(result['connected'])
                with self.assertRaises(FileExistsError):orchestration.init_context(source)
            self.assertEqual(json.loads(target.read_text())['integration_root'],str(root))

    def test_init_context_rejects_parent_link_before_any_outside_write(self):
        data=self.host_context()
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory).resolve();root=base/'repo';root.mkdir()
            outside=base/'outside';outside.mkdir();(outside/'preserve').write_text('unchanged')
            source=base/'edited.json';source.write_text(json.dumps(data))
            link=root/'.local'
            try:
                link.symlink_to(outside,target_is_directory=True)
            except OSError:
                if os.name!='nt':raise
                # Directory junction creation needs no Windows symlink privilege.
                subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(outside)],
                    check=True,capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            with patch.object(orchestration,'ROOT',root),patch.object(workspace,'ROOT',root):
                with self.assertRaisesRegex(RuntimeError,'links/reparse'):
                    orchestration.init_context(source)
            self.assertEqual([p.name for p in outside.iterdir()],['preserve'])
            self.assertEqual((outside/'preserve').read_text(),'unchanged')

    def test_init_context_rejects_hardlinked_target_without_overwriting(self):
        data=self.host_context()
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory).resolve();root=base/'repo';root.mkdir()
            outside=base/'preserve';outside.write_text('unchanged')
            source=base/'edited.json';source.write_text(json.dumps(data))
            target=root/'.local/workspace/orchestration.json';target.parent.mkdir(parents=True)
            os.link(outside,target)
            with patch.object(orchestration,'ROOT',root),patch.object(workspace,'ROOT',root):
                with self.assertRaisesRegex(RuntimeError,'alias'):
                    orchestration.init_context(source)
            self.assertEqual(outside.read_text(),'unchanged')

    def test_runtime_installer_rejects_archive_escape_and_missing_codex_resources(self):
        script=Path(__file__).parents[1]/'orchestration/install_runtime.py'
        spec=importlib.util.spec_from_file_location('runtime_installer',script)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.tar'
            with tarfile.open(path,'w') as archive:archive.addfile(tarfile.TarInfo('../escape'))
            with tarfile.open(path) as archive,self.assertRaises(ValueError):
                module.inspect_archive(archive,{'name':'test'})
            with tarfile.open(path,'w') as archive:archive.addfile(tarfile.TarInfo('bin/codex'))
            with tarfile.open(path) as archive,self.assertRaisesRegex(ValueError,'resources'):
                module.inspect_archive(archive,{'name':'codex','required_members':['bin/codex','codex-resources/bwrap']})

    def test_runtime_installer_verifies_all_bytes_before_creating_prefix(self):
        script=Path(__file__).parents[1]/'orchestration/install_runtime.py'
        spec=importlib.util.spec_from_file_location('runtime_installer',script)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        archive_bytes=io.BytesIO()
        with tarfile.open(fileobj=archive_bytes,mode='w:gz') as archive:
            member=tarfile.TarInfo('tool');member.size=4;archive.addfile(member,io.BytesIO(b'test'))
        blob=archive_bytes.getvalue()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);lock=root/'runtime.json';prefix=root/'install';bindir=root/'bin'
            asset={'name':'test','executable':'tool','url':'https://example.invalid/tool',
                   'sha256':hashlib.sha256(blob).hexdigest()}
            lock.write_text(json.dumps({'platform':'linux-amd64','assets':[{**asset,'sha256':'0'*64}]}))
            with patch.object(module.platform,'system',return_value='Linux'), \
                 patch.object(module.platform,'machine',return_value='x86_64'), \
                 patch.object(module.urllib.request,'urlopen',return_value=io.BytesIO(blob)):
                with self.assertRaisesRegex(ValueError,'SHA256'):module.install(lock,prefix,bindir)
            self.assertFalse(prefix.exists())
            # Existing command collisions fail before any network request.
            bindir.mkdir();(bindir/'tool').write_text('preserve')
            with patch.object(module.platform,'system',return_value='Linux'), \
                 patch.object(module.platform,'machine',return_value='x86_64'), \
                 patch.object(module.urllib.request,'urlopen') as download:
                with self.assertRaises(FileExistsError):module.install(lock,prefix,bindir)
                download.assert_not_called()

    def test_vm_interop_registration_does_not_override_distro_policy(self):
        config='[automount]\nenabled=false\n[interop]\nenabled=false\nappendWindowsPath=false\n'
        for registered in (False,True):
            report=boundary_report(config,' - ext4 /dev/sdb rw',1000,registered)
            self.assertTrue(report['allowed'])
            self.assertEqual(report['vm_interop_registered'],registered)
        for altered,mounts,uid in [(config,' - drvfs C: rw',1000),
                (config,' - 9p drvfs rw,aname=drvfs',1000),(config,'',0),
                (config.replace('enabled=false','enabled=true',1),'',1000),
                (config.replace('[interop]\nenabled=false','[interop]\nenabled=true'),' ',1000),
                (config.replace('appendWindowsPath=false','appendWindowsPath=true'),' ',1000),
                ('[interop]\nenabled=false','',1000)]:
            self.assertFalse(boundary_report(altered,mounts,uid,True)['allowed'])

    def test_successful_prepare_reuses_open_wave(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);receipts=root/'waves';receipts.mkdir()
            manifest={'source_head':'exact','generation':'mux-wave-123456789abc'}
            (receipts/'mux-wave-123456789abc.json').write_text(json.dumps(manifest))
            active=root/'dispatch.json';active.write_text(json.dumps(manifest))
            jobs=[{'id':'mux-wave-123456789abc','status':'open'}]
            for _ in range(2):self.assertEqual(reusable_wave(receipts,jobs,'exact',active),manifest)
            self.assertIsNone(reusable_wave(receipts,jobs,'new-source',active))
            active.write_text('{}')
            with self.assertRaises(RuntimeError):reusable_wave(receipts,jobs,'exact',active)
            jobs[0]['status']='closed'
            self.assertIsNone(reusable_wave(receipts,jobs,'exact',active))

    def test_agent_capacity_patch_does_not_modify_rig_patch(self):
        text='''[[patches.agent]]
name = "codex"
rig = "mu-core"
work_dir = "/owned/source"
max_active_sessions = 7
[[rigs]]
name = "mu-core"
'''
        updated=set_agent_field(text,'codex','','max_active_sessions',23)
        data=tomllib.loads(updated)
        self.assertEqual(data['patches']['agent'][0]['max_active_sessions'],7)
        self.assertEqual(data['patches']['agent'][1]['max_active_sessions'],23)
        self.assertEqual(data['rigs'],[{'name':'mu-core'}])
        again=set_agent_field(updated,'codex','','max_active_sessions',23)
        self.assertEqual(tomllib.loads(again),data)

    def test_update_preserves_rigs_and_unowned_provider_values(self):
        original = '''[workspace]
provider = "codex"
max_active_sessions = 3
[providers.codex]
base = "builtin:codex"
ready_delay_ms = 0
[[rigs]]
name = "validation"
prefix = "va"
[rigs.imports.gc]
source = "local-pinned-pack"
version = "sha:exact"
'''
        changed = set_field(original, 'workspace', 'max_active_sessions', 25)
        data = tomllib.loads(changed)
        before = tomllib.loads(original)
        self.assertEqual(data['rigs'], before['rigs'])
        self.assertEqual(data['providers'], before['providers'])
        self.assertEqual(data['workspace']['max_active_sessions'], 25)

    def test_insert_between_adjacent_tables_remains_valid(self):
        original = '[workspace]\n[providers.codex]\nbase = "builtin:codex"\n'
        result = set_field(original, 'workspace', 'max_active_sessions', 25)
        result = set_field(result, 'providers.codex.env', 'HTTPS_PROXY', 'http://localhost:10809')
        parsed = tomllib.loads(result)
        self.assertEqual(parsed['workspace']['max_active_sessions'], 25)
        self.assertEqual(parsed['providers']['codex']['base'], 'builtin:codex')


    def test_preparation_reports_excluded_dirty_bytes_without_rewriting_them(self):
        data={'distribution':'fixture','user':'worker','city':'/city','rig_root':'/city/mu-core'}
        status=' M owner.go\n?? local-note.txt'
        native=[subprocess.CompletedProcess([],0,'{"sessions":[]}',''),
                subprocess.CompletedProcess([],0,'[]','')]
        saved={'source_head':'a'*40,'generation':'mux-wave-old'}
        def git(*args):
            if args==('status','--porcelain','--untracked-files=all'):return status
            if args==('rev-parse','HEAD'):return 'a'*40
            self.fail('Unexpected Git operation: '+repr(args))
        with patch.object(workspace,'repository_guard'),patch.object(workspace,'git',side_effect=git), \
             patch.object(orchestration.subprocess,'run',side_effect=native), \
             patch.object(orchestration,'reusable_wave',return_value=saved),patch('builtins.print') as output:
            orchestration.prepare(data)
        result=json.loads(output.call_args.args[0])
        self.assertEqual(result['excluded_worktree_status'],status.splitlines())
        self.assertEqual(result['source_head'],'a'*40)
        self.assertTrue(result['reused'])
        self.assertNotIn('excluded_worktree_status',saved)

    def test_legacy_identity_capture_happens_once_and_preserves_bound_jobs(self):
        data={'distribution':'fixture','user':'worker','city':'/city'}
        sessions={'sessions':[{'id':'old-session','closed':False,'command':'codex'},
                              {'id':'bound-session','closed':False,'command':'/bundle/role_bootstrap.py'}]}
        items=[{'id':'old-task','status':'open','issue_type':'task','metadata':{}},
               {'id':'bound-task','status':'open','metadata':{'mu.launch_path':'/frozen'}},
               {'id':'done-task','status':'closed','metadata':{}}]
        with tempfile.TemporaryDirectory() as folder:
            context=Path(folder)/'orchestration.json'
            with patch.object(orchestration,'CONTEXT',context), \
                 patch.object(Path,'read_text',return_value=''), \
                 patch.object(orchestration.subprocess,'check_output',side_effect=[json.dumps(sessions),json.dumps(items)]) as native:
                raw=orchestration.legacy_jobs(data)
                saved=json.loads(raw)
                self.assertEqual(saved['sessions'],['old-session'])
                self.assertEqual(saved['tasks'],{'city':['old-task','done-task']})
                self.assertEqual(native.call_count,2)
            switched='[providers.codex]\ncommand="/bundle/role_bootstrap.py --legacy-record /bundle/legacy-jobs.json --legacy-sha '+hashlib.sha256(raw).hexdigest()+'"'
            with patch.object(orchestration,'CONTEXT',context),patch.object(Path,'read_text',return_value=switched), \
                 patch.object(orchestration.subprocess,'check_output') as native:
                self.assertEqual(orchestration.legacy_jobs(data),raw)
                native.assert_not_called()

    def test_failed_before_switch_retry_captures_later_legitimate_old_sessions(self):
        data={'distribution':'fixture','user':'worker','city':'/city'}
        with tempfile.TemporaryDirectory() as folder:
            context=Path(folder)/'orchestration.json'
            initial={'sessions':[{'id':'first-old','command':'codex'}]}
            later={'sessions':[{'id':'first-old','command':'codex'},{'id':'later-old','command':'codex'}]}
            with patch.object(orchestration,'CONTEXT',context),patch.object(Path,'read_text',return_value=''), \
                 patch.object(orchestration.subprocess,'check_output',side_effect=[json.dumps(initial),'[]',json.dumps(later),'[]']):
                first=orchestration.legacy_jobs(data)
                # Deployment fails before the original provider command changes.
                retried=orchestration.legacy_jobs(data)
            self.assertNotEqual(first,retried)
            self.assertEqual(json.loads(retried)['sessions'],['first-old','later-old'])
            self.assertEqual((Path(folder)/'legacy-jobs.json').read_bytes(),retried)

    def test_generated_advisers_isolate_native_overlay_slots_and_preserve_city_hooks(self):
        data={'distribution':'fixture','user':'worker','city':'/city','rig_root':'/city/mu-core'}
        with tempfile.TemporaryDirectory() as folder:
            prefix=Path(folder)/'wsl';city=prefix/'fixture/city'
            prompt=prefix/'fixture/native/prompt.template.md';prompt.parent.mkdir(parents=True)
            prompt.write_text('Native adviser prompt',encoding='utf-8')
            hooks=city/'.codex/hooks.json';hooks.parent.mkdir(parents=True)
            original=b'{"hooks":{"reviewed":"city-only"}}';hooks.write_bytes(original)
            path_type=Path
            def local_path(value):
                return prefix if value=='//wsl.localhost' else path_type(value)
            resolved='[[agent]]\nname="codex"\nprompt_template="/native/prompt.template.md"\n'
            with patch.object(orchestration,'Path',side_effect=local_path), \
                 patch.object(orchestration.subprocess,'check_output',return_value=resolved), \
                 patch.object(orchestration,'configure_trusted_projects') as trust:
                orchestration.configure_advisers(data)
            trust.assert_called_once()
            for name in ('mu-explorer','mu-reviewer','mu-deep'):
                generated=tomllib.loads((city/'agents'/name/'agent.toml').read_text(encoding='utf-8'))
                self.assertEqual(generated['work_dir'],'.gc/mu-advisers/{{.AgentBase}}')
                first=city/generated['work_dir'].replace('{{.AgentBase}}',name+'-1')
                second=city/generated['work_dir'].replace('{{.AgentBase}}',name+'-2')
                self.assertNotEqual(first,second)
                self.assertNotEqual(first,city)
                self.assertFalse(first.is_relative_to(city/'.gc/mu-inputs'))
                self.assertFalse(first.exists())  # Native Linux GC owns mkdir/overlay.
            self.assertEqual(hooks.read_bytes(),original)

    def test_single_dispatch_creates_bound_metadata_before_sling(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);packet=root/'task.json'
            task={'kind':'review','role':'mu_innovator','title':'Selected competency','body':'Inspect bounded input.'}
            packet.write_text(json.dumps(task))
            route=resolve_assignment(task)
            route={k:v for k,v in route.items() if k not in ('developer_instructions','profile_toml')}
            route.update(context_root='/frozen/tooling/.local/workspace',skills_root='/frozen/tooling/.agents/skills')
            evidence={'linux':'/frozen','source_head':'a'*40,'files':{},'manifest_sha256':'b'*64,
                'launches':{'task':{'path':'/frozen/launch.json','sha256':'c'*64,'assignment':route}}}
            native=FakeNative();data={'distribution':'fixture','user':'fixture','city':'/city'}
            with patch.object(agent_batch,'STATE',root/'state'),patch.object(agent_batch,'snapshot',return_value=evidence), \
                 patch.object(agent_batch,'Native',return_value=native),patch('builtins.print'):
                self.assertEqual(orchestration.dispatch(data,packet),0)
            self.assertEqual([call[0] for call in native.calls],['bd','sling'])
            metadata=json.loads(native.calls[0][native.calls[0].index('--metadata')+1])
            self.assertEqual(metadata['mu.role'],'mu_innovator')
            self.assertEqual(metadata['mu.launch_path'],'/frozen/launch.json')
            self.assertNotIn('--stdin',native.calls[1])


    def test_single_unknown_role_and_incomplete_write_contract_fail_before_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            packet=Path(folder)/'task.json'
            for task in ({'kind':'review','role':'bad-role','title':'T','body':'B'},
                         {'kind':'implement','role':'mu_go_worker','title':'T','body':'B'}):
                packet.write_text(json.dumps(task))
                with patch.object(agent_batch,'snapshot') as snapshot:
                    with self.assertRaises(ValueError):orchestration.dispatch({},packet)
                    snapshot.assert_not_called()



if __name__ == '__main__':
    unittest.main()
