"""Prevent runtime config updates from discarding registered workspaces."""
import tomllib
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
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


if __name__ == '__main__':
    unittest.main()
