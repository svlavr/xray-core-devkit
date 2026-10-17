"""Profile bytes, identity and execution settings must come from the actual catalog."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from role_profiles import ROOT, SUPPORTED_FEATURES, configuration_args, list_profiles, load_profile


class RoleProfileTests(unittest.TestCase):
    def test_actual_catalog_instructions_and_hashes(self):
        profiles=list_profiles()
        self.assertEqual(len(profiles),19)
        for profile in profiles:
            with self.subTest(role=profile['role']):
                raw=(ROOT/profile['profile_path']).read_bytes()
                self.assertEqual(profile['profile_sha256'],hashlib.sha256(raw).hexdigest())
                self.assertEqual(profile['profile_toml'].encode('utf-8'),raw)
                self.assertIn('Internal working language: English.',profile['developer_instructions'])
                self.assertEqual(profile['skills_root'],str(ROOT/'.agents/skills'))
                settings=dict(argument.split('=',1) for argument in configuration_args(profile)[1::2])
                self.assertEqual(json.loads(settings['developer_instructions']),profile['developer_instructions'])
                self.assertEqual(json.loads(settings['agents.enabled']),False)
                self.assertFalse({'sandbox_mode','approval_policy','provider','mcp_servers'} & settings.keys())

    def fixture(self,directory):
        root=Path(directory)
        (root/'go.mod').write_text('module github.com/xtls/xray-core\n',encoding='utf-8')
        for relative in ['.agents/orchestration/models.json','.codex/agents/mu_innovator.toml']:
            path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/relative,path)
        return root

    def test_reject_unknown_wrong_project_and_path_identifiers(self):
        for name in ['unknown','mu_missing','innovator','../mu_innovator','mu_innovator.toml',None]:
            with self.subTest(role=name),self.assertRaises(ValueError):load_profile(name)
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture(directory);(root/'go.mod').write_text('module example.org/other\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'not Xray Core'):load_profile('mu_innovator',root)

    def test_reject_unsupported_model_effort_identity_and_nested_agents(self):
        replacements=[('gpt-6.1-sol','unavailable-model'),('model_reasoning_effort = "high"','model_reasoning_effort = "ultra"'),
                      ('name = "mu_innovator"','name = "mu_security_reviewer"'),('enabled = false','enabled = true'),
                      ('gpt-6.1-sol','gpt-6-astra'),('gpt-6.1-sol','gpt-6-luna')]
        for old,new in replacements:
            with self.subTest(replacement=new),tempfile.TemporaryDirectory() as directory:
                root=self.fixture(directory);path=root/'.codex/agents/mu_innovator.toml'
                path.write_text(path.read_text(encoding='utf-8').replace(old,new),encoding='utf-8')
                with self.assertRaises(ValueError):load_profile('mu_innovator',root)

    def test_supported_features_are_applied_and_unknown_features_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture(directory);path=root/'.codex/agents/mu_innovator.toml'
            original=path.read_text(encoding='utf-8')
            reductions='\n[features]\n'+''.join(name+' = false\n' for name in sorted(SUPPORTED_FEATURES))
            path.write_text(original+reductions,encoding='utf-8')
            arguments=configuration_args(load_profile('mu_innovator',root))
            for name in SUPPORTED_FEATURES:
                self.assertIn('features.'+name+'=false',arguments)
            path.write_text(original+'\n[features]\ninvented_capability = true\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'feature'):load_profile('mu_innovator',root)

    def test_catalog_preserves_unmanaged_profiles_without_interpreting_them(self):
        from unittest.mock import patch
        import workspace
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copytree(ROOT/'.codex/agents',root/'.codex/agents')
            shutil.copytree(ROOT/'.agents/orchestration',root/'.agents/orchestration')
            (root/'go.mod').write_text('module github.com/xtls/xray-core\n', encoding='utf-8')
            extra=root/'.codex/agents/source_owned.toml'
            extra.write_text('name="source_owned"\nmodel="owner-selected"\n', encoding='utf-8')
            with patch.object(workspace,'ROOT',root):
                profiles=list_profiles(root)
            self.assertEqual({item['role'] for item in profiles},workspace.MANAGED_ROLES)
            self.assertEqual(extra.read_text(encoding='utf-8'),'name="source_owned"\nmodel="owner-selected"\n')
            (root/'go.mod').write_text('module github.com/xtls/xray-core-impostor\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'not Xray Core'):list_profiles(root)

    def test_feature_overrides_cannot_enable_inherited_capabilities(self):
        for name in SUPPORTED_FEATURES:
            with self.subTest(feature=name),tempfile.TemporaryDirectory() as directory:
                root=self.fixture(directory);path=root/'.codex/agents/mu_innovator.toml'
                path.write_text(path.read_text(encoding='utf-8')+'\n[features]\n'+name+' = true\n',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'capability reductions'):load_profile('mu_innovator',root)
            profile=load_profile('mu_innovator');profile['features']={name:True}
            with self.assertRaisesRegex(ValueError,'capability reductions'):configuration_args(profile)


if __name__=='__main__':unittest.main()
