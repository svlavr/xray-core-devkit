"""Hook automation must not trust additional or changed commands."""
import copy
from pathlib import Path
import unittest
from runtime_hooks import reviewed_hashes,reviewed_document,prepare_hooks,approved_state,native_fingerprint
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
        self.assertIn('gc --city /srv/city ',document['hooks']['PreCompact'][0]['hooks'][0]['command'])

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


if __name__=='__main__':unittest.main()
