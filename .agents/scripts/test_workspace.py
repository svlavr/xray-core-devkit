"""Offline standalone checkout, configuration and host-file safety tests."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.baseline = 'a' * 40
        self.answers = {
            ('rev-parse', '--show-toplevel'): str(self.root),
            ('branch', '--show-current'): 'main',
            ('rev-parse', 'HEAD'): self.baseline,
            ('rev-parse', '--verify', '--end-of-options', self.baseline + '^{commit}'): self.baseline,
            ('merge-base', '--is-ancestor', self.baseline, 'HEAD'): '',
            ('remote',): '',
        }
        for relative in workspace.HOST_FILES:
            self.answers[('ls-files', '--', relative)] = ''
            self.answers[('check-ignore', '--', relative)] = relative
        (self.root / 'go.mod').write_text('module github.com/xtls/xray-core\n', encoding='utf-8')
        for mocker in (patch.object(workspace, 'ROOT', self.root),
                       patch.object(workspace, 'git', side_effect=self.fake_git)):
            mocker.start()
            self.addCleanup(mocker.stop)

    def fake_git(self, *args):
        value = self.answers[args]
        if isinstance(value, Exception):
            raise value
        return value

    def setup(self, **kwargs):
        with patch.object(workspace, 'validate', return_value={'roles': 8, 'skills': 11}):
            return workspace.setup(self.root, catalog=self.root / 'absent-catalog.json', **kwargs)

    def test_fresh_official_checkout_without_private_context_or_named_remotes(self):
        result = self.setup()
        self.assertEqual(result['status'], 'VERIFIED')
        self.assertEqual(result['expected_branch'], 'main')
        self.assertEqual(result['baseline'], self.baseline)
        self.assertEqual(result['model_capabilities']['status'], 'UNKNOWN')
        self.assertEqual(workspace.policy()['baseline_kind'], 'user-selected-comparison')
        self.assertFalse((self.root / '.git').exists())

    def test_explicit_full_baseline_and_optional_public_policy(self):
        previous = 'b' * 40
        self.answers[('rev-parse', '--verify', '--end-of-options', previous + '^{commit}')] = previous
        self.answers[('merge-base', '--is-ancestor', previous, 'HEAD')] = ''
        project = self.root / '.agents/project.json'
        project.parent.mkdir()
        project.write_text(json.dumps({'public_url': 'https://example.org/source.git',
            'public_branch': 'main', 'public_push_mode': 'filtered-export-only', 'anchor': previous}))
        self.assertEqual(self.setup(baseline=previous)['baseline'], previous)
        self.assertEqual(workspace.policy()['public_push_mode'], 'filtered-export-only')
        self.assertNotIn('private_url', workspace.policy())

    def test_baseline_cli_takes_precedence_over_project_default(self):
        project = self.root / '.agents/project.json'
        project.parent.mkdir()
        project.write_text(json.dumps({'baseline': 'b' * 40}))
        self.assertEqual(self.setup(baseline=self.baseline)['baseline'], self.baseline)

    def test_partial_or_missing_baseline_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'full 40-character'):
            self.setup(baseline='abcdef0')
        self.answers[('merge-base', '--is-ancestor', self.baseline, 'HEAD')] = RuntimeError('not an ancestor')
        with self.assertRaisesRegex(RuntimeError, 'not an ancestor'):
            self.setup()

    def test_unexpected_root_module_and_detached_head_are_rejected(self):
        self.answers[('rev-parse', '--show-toplevel')] = str(self.root.parent)
        with self.assertRaisesRegex(RuntimeError, 'repository root'):
            workspace.repository_guard()
        self.answers[('rev-parse', '--show-toplevel')] = str(self.root)
        (self.root / 'go.mod').write_text('module github.com/xtls/xray-core-impostor\n')
        with self.assertRaisesRegex(RuntimeError, 'Wrong Go module'):
            workspace.repository_guard()
        self.answers[('branch', '--show-current')] = ''
        with self.assertRaisesRegex(RuntimeError, 'detached HEAD'):
            workspace.repository_guard()

    def test_verification_rejects_branch_change_but_setup_can_select_new_branch(self):
        self.setup()
        self.answers[('branch', '--show-current')] = 'feature'
        with self.assertRaisesRegex(RuntimeError, 'Unexpected working branch'):
            workspace.repository_guard()
        self.assertEqual(self.setup()['expected_branch'], 'feature')

    def test_setup_never_rewrites_git_metadata_or_remotes(self):
        self.answers[('remote',)] = 'origin'
        fetch = ('remote', 'get-url', '--all', 'origin')
        push = ('remote', 'get-url', '--push', '--all', 'origin')
        self.answers[fetch] = 'https://github.com/XTLS/Xray-core.git'
        self.answers[push] = 'https://github.com/XTLS/Xray-core.git'
        self.setup()
        self.assertEqual(workspace.policy()['remotes']['origin']['fetch'], [self.answers[fetch]])
        self.assertFalse((self.root / '.git').exists())

    def test_ignored_files_are_required_before_any_write(self):
        self.answers[('check-ignore', '--', '.codex/config.toml')] = RuntimeError('not ignored')
        with self.assertRaisesRegex(RuntimeError, 'already be ignored'):
            self.setup()
        self.assertFalse((self.root / '.local').exists())

    def test_tracked_file_is_never_overwritten(self):
        self.answers[('ls-files', '--', '.codex/config.toml')] = '.codex/config.toml'
        with self.assertRaisesRegex(RuntimeError, 'tracked host file'):
            self.setup()
        self.assertFalse((self.root / '.local').exists())

    def test_hardlink_to_source_is_rejected_before_writes(self):
        target = self.root / '.codex/config.toml'
        target.parent.mkdir()
        source = self.root / 'go.mod'
        before = source.read_bytes()
        os.link(source, target)
        with self.assertRaisesRegex(RuntimeError, 'must not alias another file'):
            self.setup()
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse((self.root / '.local').exists())

    def test_reparse_parent_is_rejected_before_writes(self):
        original = Path.lstat
        def metadata(path, *args, **kwargs):
            if path == self.root / '.codex':
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'lstat', metadata):
            with self.assertRaisesRegex(RuntimeError, 'links/reparse points'):
                self.setup()
        self.assertFalse((self.root / '.local').exists())

    def test_unknown_existing_local_config_is_preserved(self):
        config = self.root / '.codex/config.toml'
        config.parent.mkdir()
        config.write_text('user_setting = true\n')
        with self.assertRaisesRegex(RuntimeError, 'no toolkit context'):
            self.setup()
        self.assertEqual(config.read_text(), 'user_setting = true\n')

    def test_edited_generated_config_is_preserved(self):
        self.setup()
        config = self.root / '.codex/config.toml'
        content = config.read_text() + '\n# user edit\n'
        config.write_text(content, encoding='utf-8', newline='\n')
        with self.assertRaisesRegex(RuntimeError, 'was edited'):
            self.setup()
        self.assertEqual(config.read_text(), content)

    def test_optional_capability_check_never_forces_online_auth(self):
        absent = self.root / 'absent-catalog.json'
        self.assertEqual(workspace.capability_status(absent)['status'], 'UNKNOWN')
        with self.assertRaisesRegex(RuntimeError, 'catalog unavailable'):
            workspace.capability_status(absent, required=True)

    def test_git_calls_are_bounded_noninteractive_and_disable_maintenance(self):
        result = SimpleNamespace(returncode=0, stdout='value\n', stderr='')
        # Remove only this test's fake Git binding to inspect the real wrapper.
        wrapper = self._real_git
        with patch.object(workspace.subprocess, 'run', return_value=result) as invoke:
            self.assertEqual(wrapper('status', '--short'), 'value')
        self.assertEqual(invoke.call_args.kwargs['stdin'], subprocess.DEVNULL)
        self.assertEqual(invoke.call_args.kwargs['timeout'], 20)
        self.assertIn('maintenance.auto=false', invoke.call_args.args[0])

    _real_git = staticmethod(workspace.git)


class ConfigurationTests(unittest.TestCase):
    def test_full_role_and_mcp_configuration_is_retained(self):
        import tomllib
        config = tomllib.loads(workspace.configuration('python'))
        self.assertNotIn('model', config)
        self.assertNotIn('model_reasoning_effort', config)
        self.assertEqual(config['agents']['max_concurrent_threads_per_session'], 23)
        self.assertEqual(config['agents']['default_subagent_model'], 'gpt-6.1-sol')
        self.assertFalse(config['mcp_servers']['xray_gopls_android']['enabled'])
        self.assertTrue(config['mcp_servers']['xray_gopls_windows']['enabled'])
        self.assertTrue(config['mcp_servers']['xray_gitnexus']['enabled'])
        self.assertEqual(config['mcp_servers']['context7']['url'], 'https://mcp.context7.com/mcp')

    def test_repomix_requires_installed_backend_and_node(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = root / 'repomix/node_modules/repomix/bin/repomix.cjs'
            backend.parent.mkdir(parents=True)
            backend.write_text('fixture')
            self.assertIn('[mcp_servers.xray_repomix]', workspace.configuration('python', root, 'node'))
            self.assertNotIn('[mcp_servers.xray_repomix]', workspace.configuration('python', root))


if __name__ == '__main__':
    unittest.main()
