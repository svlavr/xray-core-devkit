"""Portable role discovery/generation and existing-route regression checks."""
import json
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from language_policy import WORKER_INSTRUCTIONS
from model_router import select_route
import session
import workspace


NEW_ROLES = {'mu_innovator', 'mu_design_critic', 'mu_test_architect', 'mu_agent_evaluator',
             'mu_protocol_reviewer', 'mu_concurrency_reviewer', 'mu_security_reviewer', 'mu_build_qualifier'}
NEW_SKILLS = {'xray-design-exploration', 'xray-decision-experiment', 'xray-agent-evaluation',
              'xray-protocol-compatibility', 'xray-runtime-qualification'}


class AgentWorkflowTests(unittest.TestCase):
    def copy_components(self, root):
        shutil.copytree(workspace.ROOT / '.codex/agents', root / '.codex/agents')
        shutil.copytree(workspace.ROOT / '.agents/skills', root / '.agents/skills')
        shutil.copyfile(workspace.ROOT / '.agents/CODEX_PACK.md', root / '.agents/CODEX_PACK.md')

    def test_complete_catalog_is_managed_and_generated_without_parent_override(self):
        self.assertTrue(NEW_ROLES <= workspace.MANAGED_ROLES)
        self.assertTrue(NEW_SKILLS <= workspace.MANAGED_SKILLS)
        result = workspace.validate()
        self.assertEqual((result['roles'], result['skills']), (19, 18))
        config = tomllib.loads(workspace.configuration('python'))
        self.assertNotIn('model', config)
        self.assertNotIn('model_reasoning_effort', config)
        self.assertNotIn('sandbox_mode', config)
        self.assertNotIn('approval_policy', config)
        self.assertEqual(config['agents']['max_concurrent_threads_per_session'], 23)
        self.assertEqual(config['agents']['default_subagent_model'], 'gpt-6.1-sol')
        self.assertNotIn('exa_public_research', config['mcp_servers'])
        for name in NEW_ROLES:
            self.assertEqual(config['agents'][name]['config_file'], 'agents/' + name + '.toml')
            role = tomllib.loads((workspace.ROOT / '.codex/agents' / (name + '.toml')).read_text(encoding='utf-8'))
            self.assertEqual((role['model'], role['model_reasoning_effort'], role['sandbox_mode']),
                             ('gpt-6.1-sol', 'high', 'read-only'))
            self.assertFalse(role['agents']['enabled'])
            self.assertTrue(role['developer_instructions'].lstrip().startswith(WORKER_INSTRUCTIONS))
            self.assertIn('parent session sandbox and approvals determine actual access', role['developer_instructions'])

    def test_missing_new_component_is_rejected(self):
        for relative in ('.codex/agents/mu_innovator.toml', '.codex/agents/mu_protocol_reviewer.toml',
                         '.agents/skills/xray-agent-evaluation/SKILL.md',
                         '.agents/skills/xray-runtime-qualification/SKILL.md'):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.copy_components(root)
                (root / relative).unlink()
                with patch.object(workspace, 'ROOT', root), self.assertRaisesRegex(RuntimeError, 'Missing toolkit components'):
                    workspace.validate()

    def test_new_roles_cannot_drift_model_or_enable_nesting(self):
        for old, new, error in [('model = "gpt-6.1-sol"', 'model = "gpt-6-astra"', 'Role policy mismatch'),
                                ('enabled = false', 'enabled = true', 'Nested native agents')]:
            with self.subTest(change=new), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.copy_components(root)
                path = root / '.codex/agents/mu_design_critic.toml'
                path.write_text(path.read_text(encoding='utf-8').replace(old, new), encoding='utf-8')
                with patch.object(workspace, 'ROOT', root), self.assertRaisesRegex(RuntimeError, error):
                    workspace.validate()

    def test_fresh_session_receives_actual_new_role_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.copy_components(root)
            with patch.object(workspace, 'ROOT', root):
                content = workspace.configuration('python')
            (root / '.codex/config.toml').write_text(content, encoding='utf-8')
            args = session.configuration_args(root)
            values = dict(value.split('=', 1) for value in args[1::2])
            for name in NEW_ROLES:
                actual = Path(json.loads(values[f'agents.{name}.config_file']))
                self.assertEqual(actual, (root / '.codex/agents' / (name + '.toml')).resolve())
                self.assertTrue(actual.is_file())

    def test_advisory_and_experiment_modes_reuse_existing_routes(self):
        for name in NEW_ROLES:
            route = select_route({'kind': 'review', 'body': 'Assigned competency: ' + name})
            self.assertEqual((route['action'], route['route'], route['model'], route['effort']),
                             ('DISPATCH', 'review', 'gpt-6.1-sol', 'high'))
        route = select_route({'kind': 'implement', 'body': 'mu_go_worker: explicit experimenter mode'})
        self.assertEqual((route['route'], route['model'], route['effort']), ('implement', 'gpt-6.1-sol', 'high'))
        missing = select_route({'kind': 'review', 'blocker': 'missing_input', 'body': 'mu_innovator'})
        self.assertEqual(missing['action'], 'NEEDS_CONTEXT')

    def test_progressive_runtime_references_are_discoverable(self):
        skill = workspace.ROOT / '.agents/skills/xray-runtime-qualification'
        entrypoint = (skill / 'SKILL.md').read_text(encoding='utf-8')
        for mode in ('concurrency', 'security', 'build', 'performance'):
            relative = f'references/{mode}.md'
            self.assertIn('](' + relative + ')', entrypoint)
            self.assertTrue((skill / relative).is_file())


if __name__ == '__main__':
    unittest.main()
