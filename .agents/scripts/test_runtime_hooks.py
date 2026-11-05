"""Hook automation must not trust additional or changed commands."""
import copy
import os
import queue
import subprocess
import runtime_hooks
from unittest.mock import patch
from pathlib import Path
import unittest
from runtime_hooks import reviewed_hashes,reviewed_document,prepare_hooks,approved_state,native_fingerprint,reviewed_source
import tempfile
import json
import tomllib


class HookTrustTests(unittest.TestCase):
    def test_native_fingerprint_matches_independent_pinned_codex_golden(self):
        # openai/codex rust-v0.162.0-alpha.2:
        # codex-rs/config/src/fingerprint_tests.rs L7..24. Expected digest is
        # upstream's fixed literal, not generated through reviewed_hashes.
        for source in ('rows = [{ z = 2, a = 1 }, { z = 4, a = 3 }]\n[nested]\nz = "text"\na = true\n',
                       'rows = [{ a = 1, z = 2 }, { a = 3, z = 4 }]\n[nested]\na = true\nz = "text"\n'):
            self.assertEqual(native_fingerprint(tomllib.loads(source)),
                'sha256:a5e4c8fbdbc75d185b0f2b5291bfb2de10e8c523d6c89248876fd78a97c83176')

    def test_native_event_specific_matchers_preserve_empty_precompact_only(self):
        # Actual pinned Codex hooks/list distinguishes matcher="" from null:
        # preCompact -> "", sessionStart -> "startup", userPromptSubmit -> null.
        # Capture identities before hashing so an incorrect common normalization
        # cannot make both expected and observed hashes agree accidentally.
        identities=[]
        def capture(value):
            identities.append(copy.deepcopy(value))
            return native_fingerprint(value)
        with patch.object(runtime_hooks,'native_fingerprint',side_effect=capture):
            hashes=reviewed_hashes('/srv/xray-city')
        self.assertEqual(len(hashes),4)
        precompact=next(item for item in identities if item['event_name']=='pre_compact')
        self.assertIn('matcher',precompact)
        self.assertEqual(precompact['matcher'],'')
        startup=next(item for item in identities if item['event_name']=='session_start')
        self.assertEqual(startup['matcher'],'startup')
        prompts=[item for item in identities if item['event_name']=='user_prompt_submit']
        self.assertEqual(len(prompts),2)
        self.assertTrue(all('matcher' not in item for item in prompts))
        omitted=copy.deepcopy(precompact);omitted.pop('matcher')
        self.assertNotEqual(native_fingerprint(precompact),native_fingerprint(omitted))
        for item in identities:
            self.assertEqual(item['hooks'][0]['timeout'],600)
            self.assertIs(item['hooks'][0]['async'],False)

    def test_only_exact_reviewed_project_hooks_are_accepted(self):
        root=Path('/city');source=str(root/'.codex/hooks.json')
        data={'data':[{'cwd':str(root),'hooks':[{'key':source+':'+k,'currentHash':v,
            'sourcePath':source,'source':'project','handlerType':'command','enabled':True,
            'pluginId':None,'trustStatus':'untrusted'} for k,v in reviewed_hashes('/city').items()]}]}
        self.assertEqual(len(approved_state(root,data,'/city')),4)
        changed=copy.deepcopy(data);changed['data'][0]['hooks'][0]['currentHash']='different'
        with self.assertRaises(RuntimeError):approved_state(root,changed,'/city')
        extra=copy.deepcopy(data);extra['data'][0]['hooks'].append(extra['data'][0]['hooks'][0])
        with self.assertRaises(RuntimeError):approved_state(root,extra,'/city')
        for h in data['data'][0]['hooks']:h['trustStatus']='trusted'
        self.assertEqual(approved_state(root,data,'/city'),{})

    def test_reviewed_hashes_follow_explicit_host_city_and_reject_injection(self):
        first=reviewed_hashes('/srv/first-city')
        second=reviewed_hashes('/srv/second-city')
        self.assertEqual(len(first),4)
        self.assertTrue(all(first[key]!=second[key] for key in first))
        for city in ('/srv/../other','/srv/city;echo','/srv/city name','//srv/city','/'):
            with self.assertRaises(ValueError):reviewed_hashes(city)
        document=reviewed_document('/srv/city')
        self.assertEqual(document['hooks']['SessionStart'][0]['matcher'],'startup')
        self.assertIn("gc --city '/srv/city' ",document['hooks']['PreCompact'][0]['hooks'][0]['command'])

    def test_missing_hooks_are_generated_but_changed_commands_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            prepare_hooks(root,'/srv/city')
            target=root/'.codex/hooks.json'
            self.assertEqual(json.loads(target.read_text()),reviewed_document('/srv/city'))
            prepare_hooks(root,'/srv/city')
            target.write_text('{"hooks":{}}')
            with self.assertRaisesRegex(RuntimeError,'review required'):prepare_hooks(root,'/srv/city')
            self.assertEqual(target.read_text(),'{"hooks":{}}')


    def inventory(self,root,group):
        source=str(root/'.codex/hooks.json')
        return {'data':[{'cwd':str(root),'hooks':[{'key':source+':'+key,'currentHash':value,
            'sourcePath':source,'source':'project','handlerType':'command','enabled':True,
            'pluginId':None,'trustStatus':'untrusted'} for key,value in group.items()]}]}

    def test_source_parent_hash_enabled_and_extra_inventory_controls_fail_closed(self):
        root=Path('/root');city='/srv/city';data=self.inventory(root,reviewed_hashes(city))
        changes=[('currentHash','sha256:arbitrary'),('sourcePath',str(root.parent/'.codex/hooks.json')),
                 ('source','user'),('enabled',False),('enabled','true'),('pluginId','plugin'),('pluginId',''),('handlerType','prompt')]
        for key,value in changes:
            altered=copy.deepcopy(data);altered['data'][0]['hooks'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):approved_state(root,altered,city)
        parent=copy.deepcopy(data);parent['data'][0]['cwd']=str(root.parent)
        with self.assertRaises(RuntimeError):approved_state(root,parent,city)
        extra=copy.deepcopy(data);extra['data'][0]['hooks'].append(extra['data'][0]['hooks'][0])
        with self.assertRaises(RuntimeError):approved_state(root,extra,city)

    def test_prepare_creates_only_known_template_and_rejects_changed_or_aliased_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);city='/srv/city'
            prepare_hooks(root,city);self.assertEqual(json.loads((root/'.codex/hooks.json').read_text()),reviewed_document(city))
            self.assertEqual(len(reviewed_source(root,city)),64)
            target=root/'.codex/hooks.json';target.write_text('{"hooks":{}}')
            with self.assertRaisesRegex(RuntimeError,'review required'):prepare_hooks(root,city)
            self.assertEqual(target.read_text(),'{"hooks":{}}')
            target.write_text('{"hooks":{},"hooks":'+json.dumps(reviewed_document(city)['hooks'])+'}')
            with self.assertRaisesRegex(RuntimeError,'Duplicate JSON'):prepare_hooks(root,city)
            target.unlink();outside=root/'outside.json';outside.write_text(json.dumps(reviewed_document(city)))
            os.link(outside,target)
            with self.assertRaisesRegex(RuntimeError,'unaliased'):prepare_hooks(root,city)
        for city in ('/srv/../other','/srv/city;echo','/srv/city name','//srv/city','/'):
            with self.subTest(city=city),self.assertRaises(ValueError):reviewed_hashes(city)

    def test_symlink_or_reparse_parent_is_rejected_before_creating_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);root=base/'project';root.mkdir();outside=base/'outside';outside.mkdir()
            link=root/'.codex'
            if os.name=='nt':
                result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(outside)],capture_output=True)
                if result.returncode:self.skipTest('Junction creation unavailable')
            else:link.symlink_to(outside,target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError,'alias'):prepare_hooks(root,'/srv/city')
            self.assertFalse((outside/'hooks.json').exists())

    def test_native_hash_aba_is_rejected_even_when_source_snapshot_is_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);city='/srv/city';prepare_hooks(root,city)
            target=root/'.codex/hooks.json';original=target.read_bytes();inventory=self.inventory(root,reviewed_hashes(city))
            inbox=queue.Queue();requests=[]
            class Input:
                def write(self,line):
                    request=json.loads(line);requests.append(request)
                    if request['method']=='hooks/list':
                        target.write_text('{"hooks":{}}');target.write_bytes(original)
                        altered=copy.deepcopy(inventory);altered['data'][0]['hooks'][0]['currentHash']='sha256:attacker-command'
                        result=altered
                    else:result={}
                    inbox.put(json.dumps({'id':request['id'],'result':result})+'\n')
                def flush(self):pass
            class Native:
                stdin=Input()
                def __init__(self):self.stdout=iter(lambda:inbox.get(),None)
                def terminate(self):inbox.put(None)
                def wait(self,timeout=None):return 0
            with patch.object(runtime_hooks.subprocess,'Popen',return_value=Native()):
                with self.assertRaisesRegex(RuntimeError,'reviewed Gas City template'):runtime_hooks._trust(root,city)
            self.assertFalse(any(request['method']=='config/batchWrite' for request in requests))
            self.assertEqual(target.read_bytes(),original)

    def test_old_unquoted_or_mixed_templates_are_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);city='/srv/city';prepare_hooks(root,city)
            current=reviewed_document(city)
            legacy=json.loads(json.dumps(current).replace("gc --city '"+city+"' ",'gc --city '+city+' '))
            mixed=copy.deepcopy(current);mixed['hooks']['PreCompact']=legacy['hooks']['PreCompact']
            for value in (legacy,mixed):
                target=root/'.codex/hooks.json';target.write_text(json.dumps(value));raw=target.read_bytes()
                with self.assertRaisesRegex(RuntimeError,'review required'):prepare_hooks(root,city)
                self.assertEqual(target.read_bytes(),raw)



    def test_replacement_during_native_inventory_is_rejected_before_config_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);city='/srv/city';prepare_hooks(root,city)
            target=root/'.codex/hooks.json';original=target.read_bytes();inventory=self.inventory(root,reviewed_hashes(city))
            inbox=queue.Queue();requests=[]
            class Input:
                def write(self,line):
                    request=json.loads(line);requests.append(request)
                    if request['method']=='hooks/list':
                        target.write_text('{"hooks":{}}')
                        altered=copy.deepcopy(inventory)
                        result=altered
                    else:result={}
                    inbox.put(json.dumps({'id':request['id'],'result':result})+'\n')
                def flush(self):pass
            class Native:
                stdin=Input()
                def __init__(self):self.stdout=iter(lambda:inbox.get(),None)
                def terminate(self):inbox.put(None)
                def wait(self,timeout=None):return 0
            with patch.object(runtime_hooks.subprocess,'Popen',return_value=Native()):
                with self.assertRaisesRegex(RuntimeError,'review required'):runtime_hooks._trust(root,city)
            self.assertFalse(any(request['method']=='config/batchWrite' for request in requests))
            self.assertEqual(target.read_text(),'{"hooks":{}}')


    def test_invocation_preflight_uses_exact_globals_mutable_scratch_and_never_writes_config(self):
        import resource_guard
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);city='/srv/city';prepare_hooks(root,city)
            inventory=self.inventory(root,reviewed_hashes(city))
            for hook in inventory['data'][0]['hooks']:hook['trustStatus']='trusted'
            global_args=['-C',str(root),'-c','hooks.state={}','--enable=known']
            for corrupt in (False,True):
                inbox=queue.Queue();requests=[]
                class Input:
                    def write(self,line):
                        request=json.loads(line);requests.append(request)
                        result=copy.deepcopy(inventory) if request['method']=='hooks/list' else {}
                        if corrupt and request['method']=='hooks/list':result['data'][0]['hooks'][0]['trustStatus']='untrusted'
                        inbox.put(json.dumps({'id':request['id'],'result':result})+'\n')
                    def flush(self):pass
                    def close(self):pass
                class Output:
                    def __iter__(self):return self
                    def __next__(self):
                        value=inbox.get()
                        if value is None:raise StopIteration
                        return value
                    def close(self):pass
                class Native:
                    stdin=Input();stdout=Output()
                    def poll(self):return None
                    def kill(self):inbox.put(None)
                    def wait(self,timeout=None):return 0
                with patch.object(resource_guard,'ManagedProcess',return_value=Native()) as process:
                    if corrupt:
                        with self.assertRaisesRegex(RuntimeError,'not exactly trusted'):
                            runtime_hooks.verify_invocation_hooks(root,city,global_args,expected_sha256=reviewed_source(root,city),transient=root/'source-scratch',codex='/exact/codex')
                    else:
                        self.assertEqual(runtime_hooks.verify_invocation_hooks(root,city,global_args,expected_sha256=reviewed_source(root,city),transient=root/'source-scratch',codex='/exact/codex')['trusted_hooks'],4)
                self.assertEqual(process.call_args.args[0],['/exact/codex',*global_args,'app-server','--stdio'])
                self.assertEqual(process.call_args.kwargs['transient'],root/'source-scratch')
                self.assertEqual([request['method'] for request in requests],['initialize','hooks/list'])

if __name__=='__main__':unittest.main()
