"""Profile bytes, identity and execution settings must come from the actual catalog."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from role_profiles import ROOT, SUPPORTED_FEATURES, configuration_args, list_profiles, load_profile, preset_policy, select_profile


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


    def test_five_bounded_presets_keep_full_role_and_default_identity(self):
        entries,policy_sha=preset_policy()
        self.assertEqual(len(entries),5)
        for name,entry in entries.items():
            with self.subTest(preset=name):
                base=load_profile(entry['role'])
                selected=select_profile(entry['role'],task={'kind':entry['kinds'][0],'preset':name,'bounded':True})
                self.assertEqual((selected['model'],selected['effort']),('gpt-6.1-terra','high'))
                self.assertEqual(base['model'],'gpt-6.1-sol')
                self.assertEqual(selected['profile_sha256'],base['profile_sha256'])
                self.assertTrue(selected['developer_instructions'].startswith(base['developer_instructions']))
                self.assertIn(entry['scope'],selected['developer_instructions'])
                self.assertTrue(all(item in selected['developer_instructions'] for item in entry['acceptance']))
                self.assertEqual(selected['features'],base['features'])
                self.assertEqual(selected['preset_policy_sha256'],policy_sha)
                self.assertIn('model="gpt-6.1-terra"',configuration_args(selected))
                selected['model']='gpt-6.1-sol'
                with self.assertRaisesRegex(ValueError,'identity changed'):configuration_args(selected)

    def test_unknown_mismatched_or_unbounded_presets_reject(self):
        task={'kind':'implement','preset':'native-write-fix','bounded':True}
        for change in ({'preset':None},{'preset':[]},{'preset':'unknown'},{'bounded':False},
                       {'kind':'review'},{'cross_owner':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                select_profile('mu_go_worker',task={**task,**change})
        with self.assertRaises(ValueError):select_profile('mu_reviewer',task=task)

    def test_all_presets_require_exact_bounded_scope_and_keep_default_catalog(self):
        defaults=list_profiles()
        self.assertEqual({model:sum(profile['model']==model for profile in defaults) for model in ('gpt-6.1-sol','gpt-6-luna','gpt-6-astra')},
                         {'gpt-6.1-sol':17,'gpt-6-luna':1,'gpt-6-astra':1})
        for name,entry in preset_policy()[0].items():
            valid={'preset':name,'kind':entry['kinds'][0],'bounded':True}
            for value in (None,False,1,'true'):
                bad=dict(valid)
                if value is None:bad.pop('bounded')
                else:bad['bounded']=value
                with self.subTest(preset=name,bounded=value),self.assertRaises(ValueError):select_profile(entry['role'],task=bad)
            for value in (True,None,0,'false'):
                with self.subTest(preset=name,cross_owner=value),self.assertRaises(ValueError):select_profile(entry['role'],task={**valid,'cross_owner':value})
            with self.assertRaises(ValueError):select_profile('mu_explorer',task=valid)
            forbidden=next(kind for kind in ('implement','review','explore','deep') if kind not in entry['kinds'])
            with self.assertRaises(ValueError):select_profile(entry['role'],task={**valid,'kind':forbidden})



if __name__=='__main__':unittest.main()
