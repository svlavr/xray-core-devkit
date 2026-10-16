"""Real filesystem installation/update/privacy checks using synthetic Xray trees."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import devkit


class DistributionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.bundle, self.target = self.base / 'bundle', self.base / 'source'
        self.bundle.mkdir()
        self.target.mkdir()
        (self.target / 'go.mod').write_text('module github.com/xtls/xray-core\n', encoding='utf-8')
        self.write('.agents/scripts/tool.py', 'print("owned tool")\n')
        self.write('.codex/agents/reader.toml', 'name = "reader"\n')
        self.write('.agents/dependencies/pins.json', '{"schema":1}\n')
        self.write('docs/WORKFLOW.md', 'Read source before changes.\n')
        self.write('README.md', 'Independent distribution\n')
        self.refresh()

    def write(self, name, data):
        path = self.bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding='utf-8', newline='\n')

    def refresh(self):
        (self.bundle / devkit.MANIFEST).write_text(json.dumps(devkit.build_manifest(self.bundle)), encoding='utf-8')

    def install(self, **kw):
        return devkit.install(self.target, root=self.bundle, **kw)

    def test_dry_run_is_read_only_and_dependencies_are_in_payload(self):
        before = sorted(str(p) for p in self.target.rglob('*'))
        result = self.install(dry_run=True)
        self.assertEqual(result['status'], 'PLANNED')
        self.assertIn('.agents/dependencies/pins.json', result['writes'])
        self.assertEqual(before, sorted(str(p) for p in self.target.rglob('*')))

    def test_install_preserves_user_instructions_and_records_no_source_link(self):
        (self.target / 'AGENTS.md').write_text('Human project instructions.\n', encoding='utf-8')
        self.install()
        self.assertTrue((self.target / 'AGENTS.md').read_text().startswith('Human project instructions.'))
        state = json.loads((self.target / devkit.STATE).read_text())
        self.assertNotIn('source', state)
        self.assertNotIn(str(self.bundle), json.dumps(state))
        self.assertFalse((self.target / '.codex/config.toml').exists())

    def test_conflicting_existing_tool_refuses_all_writes(self):
        target = self.target / '.agents/scripts/tool.py'
        target.parent.mkdir(parents=True)
        target.write_text('user tool', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            self.install()
        self.assertFalse((self.target / 'AGENTS.md').exists())
        self.assertEqual(target.read_text(), 'user tool')

    def test_update_only_changes_unmodified_managed_bytes(self):
        self.install()
        self.write('.agents/scripts/tool.py', 'print("updated tool")\n')
        self.refresh()
        with (self.target / 'AGENTS.md').open('a', encoding='utf-8') as handle:
            handle.write('\nNew human rule.\n')
        self.install(update=True)
        self.assertIn('updated tool', (self.target / '.agents/scripts/tool.py').read_text())
        self.assertIn('New human rule.', (self.target / 'AGENTS.md').read_text())

    def test_target_git_crlf_expansion_does_not_look_like_a_local_code_edit(self):
        self.install()
        path = self.target / '.agents/scripts/tool.py'
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        self.write('.agents/scripts/tool.py', 'print("new distribution")\n')
        self.refresh()
        self.install(update=True)
        self.assertEqual(path.read_bytes(), b'print("new distribution")\n')

    def test_update_preserves_modified_managed_tool_and_instructions(self):
        self.install()
        (self.target / '.agents/scripts/tool.py').write_text('local improvement\n', encoding='utf-8')
        self.write('.agents/scripts/tool.py', 'new distribution\n')
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Preserved'):
            self.install(update=True)
        self.assertEqual((self.target / '.agents/scripts/tool.py').read_text(), 'local improvement\n')

    def test_modified_managed_guidance_refuses_update(self):
        self.install()
        path = self.target / 'AGENTS.md'
        path.write_text(path.read_text().replace('No publication', 'Automatic publication'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'were edited'):
            self.install(update=True)

    def test_hardlinked_target_is_rejected_without_touching_peer(self):
        peer = self.base / 'unrelated.txt'
        peer.write_text('other work', encoding='utf-8')
        os.link(peer, self.target / 'AGENTS.md')
        with self.assertRaisesRegex(ValueError, 'aliased'):
            self.install()
        self.assertEqual(peer.read_text(), 'other work')
        self.assertFalse((self.target / '.agents').exists())

    def test_bundle_mutation_or_sensitive_payload_refuses_packaging(self):
        self.write('.agents/scripts/tool.py', 'unexpected\n')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            devkit.verify(self.bundle)
        self.refresh()
        self.write('.agents/auth.json', '{"secret":"synthetic"}')
        with self.assertRaisesRegex(ValueError, 'Credential'):
            devkit.build_manifest(self.bundle)

    def test_archive_contains_only_manifest_allowlist_not_host_state_or_git(self):
        self.write('.local/personal.txt', 'synthetic host data')
        self.write('.git/config', 'synthetic git identity')
        self.write('unreviewed.txt', 'not public')
        output = self.base / 'public.zip'
        devkit.archive(output, self.bundle)
        with zipfile.ZipFile(output) as handle:
            names = handle.namelist()
            self.assertIn('xray-core-devkit/devkit-manifest.json', names)
            self.assertFalse(any('/.local/' in n or '/.git/' in n or 'unreviewed' in n for n in names))

    def test_failed_atomic_replacement_preserves_old_bytes_and_retry_works(self):
        self.install()
        self.write('.agents/scripts/tool.py', 'new distribution\n')
        self.refresh()
        real_replace = os.replace
        def interrupted(source, destination):
            if str(destination).endswith('tool.py'):
                raise OSError('synthetic interrupted replacement')
            return real_replace(source, destination)
        with patch.object(devkit.os, 'replace', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'interrupted'):
                self.install(update=True)
        self.assertEqual((self.target / '.agents/scripts/tool.py').read_text(), 'print("owned tool")\n')
        self.assertFalse(list(self.target.rglob('.devkit-*.tmp')))
        self.install(update=True)
        self.assertEqual((self.target / '.agents/scripts/tool.py').read_text(), 'new distribution\n')

    def test_retry_after_state_write_failure_accepts_new_guidance(self):
        self.install()
        original = devkit.atomic_write
        def interrupted(path, data):
            if path.name == 'devkit-install.json':
                raise OSError('synthetic state failure')
            return original(path, data)
        with patch.object(devkit, 'GUIDANCE', devkit.GUIDANCE + '\nA newly reviewed rule.'):
            with patch.object(devkit, 'atomic_write', side_effect=interrupted):
                with self.assertRaisesRegex(OSError, 'state failure'):
                    self.install(update=True)
            self.install(update=True)
            self.assertIn('newly reviewed', (self.target / 'AGENTS.md').read_text())


if __name__ == '__main__':
    unittest.main()
