"""Offline export guards plus one bounded real Git object/index exercise."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid
import tempfile
import subprocess

import public_export as export

POLICY = {'schema': 1, 'public_anchor': 'c' * 40,
          'public_url': 'https://example.invalid/owner/export.git',
          'public_ref': 'refs/heads/export', 'anchor_ref': 'refs/heads/anchor', 'ci_blobs': {}}

class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.entry = ('100644', 'blob', '1' * 40)
        self.manifest = {'paths': ['main/main.go'], 'ci_blobs': {}}

    def test_private_files_are_excluded(self):
        source = {'main/main.go': self.entry}
        for path in ['.private/token.txt', '.agents/skills/a/SKILL.md', '.codex/config.toml',
                     '.local/provider.json', 'AGENTS.override.md', 'sub/.env.secret']:
            source[path] = self.entry
        self.assertEqual(export.select(source, self.manifest), {'main/main.go': self.entry})

    def test_even_explicit_allowlist_cannot_publish_private_file(self):
        for path in ['.private/token.txt', '.AGENTS/role.md', 'nested/AGENTS.override.md', '.env.key']:
            with self.subTest(path=path), self.assertRaisesRegex(RuntimeError, 'Private path'):
                export.select({path: self.entry}, {'paths': [path], 'ci_blobs': {}})

    def test_new_public_source_requires_manifest_decision(self):
        with self.assertRaisesRegex(RuntimeError, 'unlisted'):
            export.select({'main/main.go': self.entry, 'measurement/new.go': self.entry}, self.manifest)

    def test_omitted_required_source_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            export.select({}, self.manifest)

    def test_symlinks_and_submodules_are_rejected(self):
        for mode, kind in [('120000', 'blob'), ('160000', 'commit')]:
            with self.subTest(mode=mode), self.assertRaisesRegex(RuntimeError, 'Symlink/submodule'):
                export.select({'main/main.go': (mode, kind, '1' * 40)}, self.manifest)

    def test_unreviewed_workflow_is_rejected(self):
        path = '.github/workflows/release.yml'
        with self.assertRaisesRegex(RuntimeError, 'reviewed blob pin'):
            export.select({path: self.entry}, {'paths': [path], 'ci_blobs': {}})

    def test_changed_reviewed_workflow_is_rejected(self):
        path = '.github/workflows/test.yml'
        with self.assertRaisesRegex(RuntimeError, 'CI changed'):
            export.select({path: self.entry}, {'paths': [path], 'ci_blobs': {path: '2' * 40}})

    def test_path_aliases_and_traversal_are_rejected(self):
        for path in ['../main.go', '/main.go', 'core/../main.go', 'C:/secret', 'main.go.', 'main.go ', 'a\nb']:
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                export.safe_path(path)

    def test_case_alias_in_committed_manifest_is_rejected(self):
        data = {**POLICY, 'paths': ['core/a.go', 'CORE/a.go']}
        with patch.object(export, 'run', return_value=json.dumps(data).encode()):
            with self.assertRaisesRegex(RuntimeError, 'case-aliased'):
                export.load_manifest('1' * 40)

    def test_non_sha_input_is_rejected(self):
        for value in ['HEAD', '--all', 'a' * 39, '../secret']:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                export.oid(value)

class PolicyTests(unittest.TestCase):
    def test_explicit_destination_refs_anchor_and_ci_policy_required(self):
        export.validate_policy(POLICY)
        for key in ('public_anchor', 'public_url', 'public_ref', 'anchor_ref', 'ci_blobs'):
            manifest = {k: v for k, v in POLICY.items() if k != key}
            with self.subTest(missing=key), self.assertRaises(RuntimeError):
                export.validate_policy(manifest)
        for key, value in [('public_url', 'https://user:secret@example.invalid/export.git'),
                           ('public_url', 'file:///tmp/export.git'),
                           ('public_url', 'https://example.invalid/../export.git'),
                           ('public_ref', 'refs/heads/../other'),
                           ('anchor_ref', 'refs/heads/test.lock'),
                           ('public_ref', '--all')]:
            with self.subTest(key=key, value=value), self.assertRaises(RuntimeError):
                export.validate_policy({**POLICY, key: value})

    def test_clean_source_requires_opt_in_and_agreed_policy(self):
        with patch.object(export, 'repository_guard', return_value={}):
            with self.assertRaisesRegex(RuntimeError, 'Explicit filtered'):
                export.clean_source()
        with patch.object(export, 'repository_guard', return_value={
                 'public_push_mode': 'filtered-export-only', 'public_url': 'https://example.invalid/other.git'}), \
             patch.object(export, 'run', side_effect=[b'', ('a' * 40).encode()]), \
             patch.object(export, 'load_manifest', return_value=(POLICY, 'digest')):
            with self.assertRaisesRegex(RuntimeError, 'differs from project policy'):
                export.clean_source()

    def test_worker_state_blocks_inherited_publication_policy_before_export_operations(self):
        inherited = {'public_push_mode': 'filtered-export-only',
                     'public_url': POLICY['public_url'], 'public_branch': POLICY['public_ref'],
                     'anchor': POLICY['public_anchor']}
        with tempfile.TemporaryDirectory(prefix='export-worker-guard-') as scratch:
            root = Path(scratch)
            marker = root / '.local/workspace/worker.json'
            for state in ('context-worker-flag', 'worker-marker'):
                if state == 'worker-marker':
                    marker.parent.mkdir(parents=True, exist_ok=True)
                    marker.write_text('{}', encoding='utf-8')
                selection = {**inherited, **({'worker': True} if state == 'context-worker-flag' else {})}
                for operation in ('clean_source', 'prepare', 'publish'):
                    with self.subTest(state=state, operation=operation), \
                         patch.object(export, 'ROOT', root), \
                         patch.object(export, 'repository_guard', return_value=selection) as repository, \
                         patch.object(export, 'load_manifest', return_value=({**POLICY, 'paths': ['main.go']}, 'digest')) as manifest, \
                         patch.object(export, 'run') as git, \
                         patch.object(export, 'remote_head') as remote, \
                         patch.object(export, 'build_tree') as tree, \
                         patch.object(export, 'validate_candidate') as candidate:
                        with self.assertRaisesRegex(RuntimeError, 'Worker checkouts cannot'):
                            if operation == 'prepare':
                                export.prepare('Reviewed synthetic export')
                            elif operation == 'publish':
                                export.publish(root / 'missing-receipt.json')
                            else:
                                export.clean_source()
                        manifest.assert_not_called()
                        git.assert_not_called()
                        remote.assert_not_called()
                        tree.assert_not_called()
                        candidate.assert_not_called()
                        if state == 'worker-marker':
                            repository.assert_not_called()

    def test_integrating_owner_keeps_explicit_clean_source_path(self):
        selection = {'public_push_mode': 'filtered-export-only',
                     'public_url': POLICY['public_url'], 'public_branch': POLICY['public_ref'],
                     'anchor': POLICY['public_anchor']}
        with tempfile.TemporaryDirectory(prefix='export-integrator-guard-') as scratch, \
             patch.object(export, 'ROOT', Path(scratch)), \
             patch.object(export, 'repository_guard', return_value=selection), \
             patch.object(export, 'run', side_effect=[b'', ('a' * 40).encode()]), \
             patch.object(export, 'load_manifest', return_value=(POLICY, 'digest')):
            self.assertEqual(export.clean_source(), 'a' * 40)

    def test_dirty_source_and_wrong_remote_response_block(self):
        with patch.object(export, 'repository_guard', return_value={'public_push_mode': 'filtered-export-only'}), \
             patch.object(export, 'run', return_value=b' M main.go'):
            with self.assertRaisesRegex(RuntimeError, 'Commit and review'):
                export.clean_source()
        with patch.object(export, 'destination_guard'), patch.object(export, 'run',
                return_value=('a' * 40 + '\trefs/heads/wrong\n').encode()):
            with self.assertRaisesRegex(RuntimeError, 'Unexpected remote'):
                export.remote_head(POLICY)

    def test_linear_public_history_rejects_merges_and_private_commits(self):
        candidate, source = 'a' * 40, 'f' * 40
        for line in [f'{candidate} {POLICY["public_anchor"]} {source}',
                     f'{source} {POLICY["public_anchor"]}']:
            def git(*args, **kwargs):
                if args[0] == 'merge-base':
                    return b''
                if args[:2] == ('rev-list', '--reverse'):
                    return (line + '\n').encode()
                return (source + '\n').encode()
            with patch.object(export, 'run', side_effect=git), patch.object(export, 'entries', return_value={}):
                with self.assertRaisesRegex(RuntimeError, 'private commit, merge'):
                    export.public_history(candidate, source, {**POLICY, 'paths': ['main.go']})


class HistoricalEntryTests(unittest.TestCase):
    def setUp(self):
        self.blob = '1' * 40
        self.manifest = {**POLICY, 'paths': ['main/main.go'], 'ci_blobs': {},
                         'historical_only': {'retired.go': [{'mode': '100644', 'blob': self.blob}]}}

    def history(self, entry):
        candidate, source = 'a' * 40, 'f' * 40
        def git(*args, **kwargs):
            if args[0] == 'merge-base':
                return b''
            if args[:2] == ('rev-list', '--reverse'):
                return f'{candidate} {POLICY['public_anchor']}\n'.encode()
            if args[0] == 'rev-list':
                return (source + '\n').encode()
            self.fail('unexpected Git operation')
        def tree(commit):
            ordinary = {'main/main.go': ('100644', 'blob', '2' * 40)}
            return ordinary if commit == POLICY['public_anchor'] else {**ordinary, 'retired.go': entry}
        with patch.object(export, 'run', side_effect=git), patch.object(export, 'entries', side_effect=tree):
            export.public_history(candidate, source, self.manifest)

    def test_exact_retired_public_blob_is_admitted_only_in_history(self):
        self.history(('100644', 'blob', self.blob))
        selected = export.select({'main/main.go': ('100644', 'blob', '2' * 40)}, self.manifest)
        self.assertNotIn('retired.go', selected)

    def test_changed_historical_blob_or_mode_is_rejected(self):
        for entry in [('100644', 'blob', '3' * 40), ('100755', 'blob', self.blob),
                      ('120000', 'blob', self.blob), ('160000', 'commit', self.blob)]:
            with self.subTest(entry=entry), self.assertRaisesRegex(RuntimeError, 'Unreviewed'):
                self.history(entry)

    def test_retired_path_in_current_source_still_requires_live_admission(self):
        source = {'main/main.go': ('100644', 'blob', '2' * 40),
                  'retired.go': ('100644', 'blob', self.blob)}
        with self.assertRaisesRegex(RuntimeError, 'unlisted'):
            export.select(source, self.manifest)

    def test_private_unsafe_alias_or_live_overlap_historical_paths_are_rejected(self):
        for paths in [dict.fromkeys(['.private/key'], self.manifest['historical_only']['retired.go']),
                      dict.fromkeys(['../key'], self.manifest['historical_only']['retired.go']),
                      dict.fromkeys(['retired.go', 'RETIRED.go'], self.manifest['historical_only']['retired.go']),
                      dict.fromkeys(['main/main.go'], self.manifest['historical_only']['retired.go'])]:
            with self.subTest(paths=paths), self.assertRaises(RuntimeError):
                export.historical_entries({**self.manifest, 'historical_only': paths})

    def test_invalid_or_duplicate_historical_records_are_rejected(self):
        good = {'mode': '100644', 'blob': self.blob}
        for records in [[], [good, good], [{'mode': '120000', 'blob': self.blob}],
                        [{'mode': '100644', 'blob': 'HEAD'}], [{**good, 'extra': 1}], 'not-a-list']:
            with self.subTest(records=records), self.assertRaises(RuntimeError):
                export.historical_entries({**self.manifest, 'historical_only': {'retired.go': records}})


class GitObjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='export-fixture-')
        cls.root = Path(cls.scratch.name).resolve()
        cls.root_patch = patch.object(export, 'ROOT', cls.root)
        cls.root_patch.start()
        cls.target_patch = patch.object(export, 'host_target', side_effect=lambda p: cls.root / p)
        cls.target_patch.start()
        export.run('init', '-q')
        export.run('config', 'user.name', 'Export fixture')
        export.run('config', 'user.email', 'fixture@example.invalid')
        export.run('config', 'core.autocrlf', 'false')
        export.run('config', 'core.hooksPath', str(cls.root / 'empty-hooks'))
        (cls.root / 'main.go').write_text('package main\n', encoding='utf-8')
        export.run('add', 'main.go')
        export.run('commit', '-qm', 'Synthetic anchor')
        cls.head = export.run('rev-parse', 'HEAD').decode().strip()
        cls.anchor = cls.head
        cls.index = cls.root / '.git/index'
        cls.index_hash = hashlib.sha256(cls.index.read_bytes()).hexdigest()
        cls.original = export.entries(cls.anchor)
        manifest = {**POLICY, 'public_anchor': cls.anchor, 'paths': sorted(cls.original),
                    'ci_blobs': {}}
        raw = (json.dumps(manifest, indent=2) + '\n').encode()
        manifest_blob = export.run('hash-object', '-w', '--stdin', data=raw).decode().strip()
        secret_blob = export.run('hash-object', '-w', '--stdin', data=b'INTENTIONAL_PRIVATE_TEST_SENTINEL\n').decode().strip()
        private = dict(cls.original)
        private[export.MANIFEST] = ('100644', 'blob', manifest_blob)
        private['.private/test-secret.txt'] = ('100644', 'blob', secret_blob)
        tree = export.build_tree(private)
        cls.source = export.run('commit-tree', tree, '-p', cls.head, '-m', 'test private fixture').decode().strip()
        selected = export.select(export.entries(cls.source), manifest)
        cls.public_tree = export.build_tree(selected)
        cls.candidate = export.run('commit-tree', cls.public_tree, '-p', cls.anchor, '-m', 'test public fixture').decode().strip()
        cls.receipt = {'schema': 1, 'private_sha': cls.source, 'public_sha': cls.candidate,
                       'public_ref': manifest['public_ref'], 'public_url': manifest['public_url'],
                       'expected_remote': None, 'tree': cls.public_tree,
                       'manifest_sha256': hashlib.sha256(raw).hexdigest(),
                       'files': [{'path': p, 'mode': e[0], 'blob': e[2]} for p, e in sorted(selected.items())]}
        cls.manifest = manifest

    @classmethod
    def tearDownClass(cls):
        try:
            assert export.run('rev-parse', 'HEAD').decode().strip() == cls.head
            assert hashlib.sha256(cls.index.read_bytes()).hexdigest() == cls.index_hash
        finally:
            cls.target_patch.stop()
            cls.root_patch.stop()
            cls.scratch.cleanup()

    def test_actual_filter_omits_private_sentinel_and_preserves_every_public_blob(self):
        selected = export.validate_candidate(self.receipt, self.source)
        self.assertEqual(selected, self.original)
        self.assertEqual(export.run('rev-parse', self.anchor + '^{tree}').decode().strip(), self.public_tree)

    def test_public_tree_with_private_parent_is_rejected(self):
        bad = export.run('commit-tree', self.public_tree, '-p', self.source, '-m', 'test forbidden ancestry').decode().strip()
        receipt = dict(self.receipt, public_sha=bad, expected_remote=self.source)
        with self.assertRaisesRegex(RuntimeError, 'private commit'):
            export.validate_candidate(receipt, self.source)

    def test_tampered_blob_receipt_is_rejected(self):
        receipt = dict(self.receipt, files=[])
        with self.assertRaisesRegex(RuntimeError, 'Per-file provenance'):
            export.validate_candidate(receipt, self.source)

    def test_remote_movement_refuses_push(self):
        path = export.host_target('.local/export/test-receipt-' + uuid.uuid4().hex + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.receipt), encoding='utf-8')
        try:
            with patch.object(export, 'clean_source', return_value=self.source), \
                 patch.object(export, 'validate_candidate', return_value={}), \
                 patch.object(export, 'load_manifest', return_value=(self.manifest, 'unused')), \
                 patch.object(export, 'remote_head', return_value='2' * 40), \
                 patch.object(export, 'run') as git:
                with self.assertRaisesRegex(RuntimeError, 'Public ref changed'):
                    export.publish(path)
                git.assert_not_called()
        finally:
            path.unlink()

    def test_destination_receipt_drift_is_rejected(self):
        for key, value in [('public_url', 'https://example.invalid/wrong.git'),
                           ('public_ref', 'refs/heads/wrong'), ('manifest_sha256', 'wrong')]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                export.validate_candidate({**self.receipt, key: value}, self.source)

    def test_publish_uses_exact_candidate_destination_and_is_idempotent(self):
        path = export.host_target('.local/export/publish-fixture.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.receipt), encoding='utf-8')
        with patch.object(export, 'clean_source', return_value=self.source), \
             patch.object(export, 'validate_candidate'), \
             patch.object(export, 'load_manifest', return_value=(self.manifest, 'unused')), \
             patch.object(export, 'remote_head', side_effect=[None, self.candidate]), \
             patch.object(export, 'destination_guard') as guard, patch.object(export, 'run') as git:
            self.assertEqual(export.publish(path)[0], 'PUBLISHED')
            guard.assert_called_once_with(self.manifest)
            git.assert_called_once_with('push', self.manifest['public_url'],
                                        self.candidate + ':' + self.manifest['public_ref'], timeout=90)
        with patch.object(export, 'clean_source', return_value=self.source), \
             patch.object(export, 'validate_candidate'), \
             patch.object(export, 'load_manifest', return_value=(self.manifest, 'unused')), \
             patch.object(export, 'remote_head', return_value=self.candidate), patch.object(export, 'run') as git:
            self.assertEqual(export.publish(path)[0], 'ALREADY_PUBLISHED')
            git.assert_not_called()

    def test_actual_git_push_url_rewrite_is_rejected_without_network(self):
        real = export.run
        def rewritten(*args, **kwargs):
            return real('-c', 'url.https://example.invalid/wrong.pushInsteadOf=' + self.manifest['public_url'], *args, **kwargs)
        with patch.object(export, 'run', side_effect=rewritten):
            with self.assertRaisesRegex(RuntimeError, 'URL rewrite'):
                export.destination_guard(self.manifest)

    def test_actual_git_fetch_url_rewrite_is_rejected_without_network(self):
        real = export.run
        def rewritten(*args, **kwargs):
            return real('-c', 'url.https://example.invalid/wrong.insteadOf=' + self.manifest['public_url'], *args, **kwargs)
        with patch.object(export, 'run', side_effect=rewritten):
            with self.assertRaisesRegex(RuntimeError, 'URL rewrite'):
                export.destination_guard(self.manifest)

if __name__ == '__main__':
    unittest.main()
