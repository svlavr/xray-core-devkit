"""Real-Git checks for the source-size receipt; fixtures never touch primary Git."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from source_size import Repo, build, catalog_read, report, startup_check, verify


class SourceSizeTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[2] / '.local/source-size-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='owned-', dir=scratch)
        self.root = Path(temp.name).resolve()
        assert self.root.is_relative_to(scratch.resolve())
        self.addCleanup(temp.cleanup)
        self.repo = Repo(self.root)
        self.repo.git('init', '-q')
        self.repo.git('config', 'user.name', 'Size fixture')
        self.repo.git('config', 'user.email', 'fixture@example.invalid')
        self.repo.git('config', 'core.autocrlf', 'false')
        self.repo.git('config', 'core.hooksPath', str(self.root / 'empty-hooks'))
        self.catalog = {'schema': 1, 'modules': {
            'measurement': {'prefixes': ['measurement/'], 'paths': []},
            'statistics_control': {'prefixes': ['stats/'], 'paths': []},
            'dns': {'prefixes': ['dns/'], 'paths': []}}, 'shared_fork_paths': []}
        self.write('dns/native.go', b'one\ntwo\nthree\n')
        self.write('common/native.go', b'original\n')
        self.write('.gitattributes', b'*.go -diff\n')
        self.commit('upstream')
        self.upstream = self.repo.commit('HEAD')
        self.write('.agents/metrics/modules.json', json.dumps(self.catalog).encode())
        self.repo.git('add', '.agents/metrics/modules.json')

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def commit(self, message):
        self.repo.git('add', '-A')
        self.repo.git('commit', '-qm', message)

    def measure(self, source='INDEX'):
        return build(self.repo, source, self.upstream, self.catalog)

    def rows(self, snap):
        return {row['path']: row for row in snap['files']}

    def save_receipt(self, snap):
        self.write('.agents/metrics/source-size.json', json.dumps(snap).encode())

    def test_absent_catalog_is_uninitialized_and_partial_catalog_blocks(self):
        self.assertEqual(startup_check(self.repo)['status'], 'UNINITIALIZED')
        self.commit('catalog only')
        with self.assertRaisesRegex(ValueError, 'Missing tracked'):
            startup_check(self.repo)

    def test_user_modules_and_catalog_changes_remain_explicit(self):
        self.catalog['modules'] = {'feature': {'prefixes': ['dns/'], 'paths': []}}
        before = self.measure()
        self.assertIn('feature', before['modules'])
        self.catalog['modules']['second'] = {'paths': [], 'prefixes': []}
        after = self.measure()
        self.assertEqual(report(before, after)['delta']['second']['runtime']['net'], 0)

    def test_staged_blobs_ignore_unstaged_untracked_and_intent_to_add(self):
        self.write('dns/native.go', b'one\nreplaced\nthree\n')
        self.write('dns/space name.go', b'line\r\nlast')
        self.write('dns/empty.go', b'')
        self.repo.git('add', 'dns/native.go', 'dns/space name.go', 'dns/empty.go')
        self.write('dns/native.go', b'unstaged\nextra\nlines\nmore\n')
        self.write('dns/intent.go', b'not staged\n')
        self.repo.git('add', '-N', 'dns/intent.go')
        self.write('dns/untracked.go', b'ignored candidate\n')
        snap = self.measure()
        rows = self.rows(snap)
        self.assertEqual((rows['dns/native.go']['lines'], rows['dns/native.go']['added'],
                          rows['dns/native.go']['deleted']), (3, 1, 1))
        self.assertEqual(rows['dns/space name.go']['lines'], 2)
        self.assertTrue(rows['dns/empty.go']['present'])
        self.assertEqual(rows['dns/empty.go']['lines'], 0)
        self.assertNotIn('dns/intent.go', rows)
        self.assertNotIn('dns/untracked.go', rows)
        self.assertEqual(self.rows(self.measure(self.upstream))['dns/native.go']['added'], 0)

    def test_deletion_and_rename_keep_lengths_and_nonduplicated_totals(self):
        before = self.measure()
        self.repo.git('mv', 'dns/native.go', 'dns/moved.go')
        after = self.measure()
        rows = self.rows(after)
        self.assertFalse(rows['dns/native.go']['present'])
        self.assertEqual((rows['dns/native.go']['lines'], rows['dns/native.go']['deleted']), (0, 3))
        self.assertEqual((rows['dns/moved.go']['lines'], rows['dns/moved.go']['added']), (3, 3))
        self.assertEqual(after['modules']['dns']['runtime']['net'], 0)
        self.assertEqual(after['modules']['dns']['runtime']['files'], 1)
        comparison = report(before, after)
        self.assertEqual(len([r for r in comparison['changed_files'] if r['category'] == 'runtime']), 2)

    def test_binary_and_categories_are_explicit(self):
        self.write('dns/native_test.go', b'test\n')
        self.write('dns/config.pb.go', b'generated\n')
        self.write('testing/helper.go', b'helper\n')
        self.write('.agents/helper.py', b'tool\n')
        self.write('asset.bin', b'\0bytes\n')
        self.repo.git('add', '-A')
        snap = self.measure()
        rows = self.rows(snap)
        self.assertEqual(rows['dns/native_test.go']['category'], 'tests')
        self.assertEqual(rows['dns/config.pb.go']['category'], 'generated')
        self.assertEqual(rows['testing/helper.go']['category'], 'test_support')
        self.assertEqual(rows['.agents/helper.py']['category'], 'tooling')
        self.assertIsNone(rows['asset.bin']['added'])
        self.assertIsNone(rows['asset.bin']['net'])
        self.assertTrue(snap['modules']['shared']['other']['partial'])
        self.assertEqual(snap['modules']['shared']['other']['unknown_fork_files'], 1)

    def test_new_unmapped_and_overlapping_owners_fail(self):
        self.write('common/new.go', b'new\n')
        self.repo.git('add', 'common/new.go')
        with self.assertRaisesRegex(ValueError, 'Unmapped fork runtime'):
            self.measure()
        self.catalog['shared_fork_paths'].append('common/new.go')
        snap = self.measure()
        self.assertEqual(snap['modules']['shared']['runtime']['net'], 1)
        self.catalog['modules']['measurement']['paths'].append('dns/native.go')
        with self.assertRaisesRegex(ValueError, 'Ambiguous module owner'):
            self.measure()

    def test_unchanged_upstream_binary_keeps_component_total_partial(self):
        self.write('asset.bin', b'\0unchanged\n')
        self.commit('upstream binary')
        self.upstream = self.repo.commit('HEAD')
        snap = self.measure()
        row = self.rows(snap)['asset.bin']
        self.assertIsNone(row['lines'])
        self.assertFalse(row['fork_changed'])
        totals = snap['modules']['shared']['other']
        self.assertTrue(totals['partial'])
        self.assertEqual(totals['binary_files'], 1)
        self.assertEqual(totals['unknown_fork_files'], 0)
        self.assertEqual(totals['net'], 0)
        self.assertTrue(snap['totals']['other']['partial'])

    def test_receipt_self_exclusion_and_two_metadata_commits(self):
        self.write('dns/native.go', b'changed\n')
        self.repo.git('add', 'dns/native.go')
        snap = self.measure()
        self.save_receipt(snap)
        self.commit('source with receipt')
        self.assertEqual(verify(self.repo), snap)
        for number in (1, 2):
            self.write('.agents/metrics/checkpoint.json', json.dumps({'number': number}).encode())
            self.commit('metadata only')
            self.assertEqual(verify(self.repo), snap)
            self.assertEqual(startup_check(self.repo)['status'], 'VERIFIED_HEAD')
        self.write('dns/native.go', b'equal length but different\n')
        self.commit('missing new receipt')
        with self.assertRaisesRegex(ValueError, 'stale'):
            verify(self.repo)

    def test_docs_refresh_reuses_runtime_identity_and_catalog_changes_are_visible(self):
        first = self.measure()
        self.write('README.md', b'new documentation\n')
        self.repo.git('add', 'README.md')
        second = self.measure()
        delta = report(first, second)
        self.assertTrue(delta['runtime_unchanged'])
        self.assertNotEqual(first['source_fingerprint'], second['source_fingerprint'])
        self.catalog['shared_fork_paths'].append('common/future.go')
        third = self.measure()
        self.assertTrue(report(second, third)['catalog_changed'])

    def test_concurrent_staging_is_rejected(self):
        original = self.repo.blobs
        mutated = False

        def blobs(oids):
            nonlocal mutated
            data = original(oids)
            if not mutated:
                mutated = True
                self.write('dns/native.go', b'concurrent update\n')
                self.repo.git('add', 'dns/native.go')
            return data

        with patch.object(self.repo, 'blobs', blobs):
            with self.assertRaisesRegex(ValueError, 'changed during measurement'):
                self.measure()

    def test_metadata_staged_after_receipt_read_is_rejected(self):
        for changed_path in ('.agents/metrics/source-size.json', '.agents/metrics/modules.json'):
            with self.subTest(path=changed_path):
                self.write('.agents/metrics/modules.json', json.dumps(self.catalog).encode())
                self.save_receipt(self.measure())
                self.repo.git('add', '.agents/metrics')
                original = self.repo.text_from_tree
                mutated = False

                def text_from_tree(view, path):
                    nonlocal mutated
                    data = original(view, path)
                    if path == changed_path and not mutated:
                        mutated = True
                        self.write(changed_path, b'{"schema": 99}')
                        self.repo.git('add', changed_path)
                    return data

                with patch.object(self.repo, 'text_from_tree', text_from_tree):
                    with self.assertRaisesRegex(ValueError, 'changed during verification'):
                        verify(self.repo, 'INDEX')

    def test_baseline_shift_and_utf8_path_are_not_hidden(self):
        before = self.measure()
        name = 'dns/' + '\u043f\u0440\u0438\u043c\u0435\u0440.go'
        self.write(name, b'utf8 path\n')
        self.repo.git('add', name)
        after = self.measure()
        self.assertIn(name, self.rows(after))
        self.commit('new source')
        new_base = self.repo.commit('HEAD')
        rebased = build(self.repo, new_base, new_base, self.catalog)
        self.assertTrue(report(before, rebased)['baseline_changed'])
        self.assertEqual(rebased['modules']['dns']['runtime']['net'], 0)


if __name__ == '__main__':
    unittest.main()
