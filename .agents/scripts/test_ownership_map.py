"""Offline semantic ownership checks against synthetic immutable file facts."""
import json
import unittest
from unittest.mock import patch

import ownership_map
import source_size


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.head = 'a' * 40
        self.row = {'path': 'common/example.go', 'module': 'shared', 'category': 'runtime',
                    'fork_changed': True, 'blob': 'b' * 40, 'lines': 4, 'upstream_lines': 3,
                    'added': 2, 'deleted': 1, 'net': 1}
        self.snapshot = {'upstream_sha': 'c' * 40, 'runtime_fingerprint': 'synthetic-fingerprint',
                         'files': [self.row]}
        self.catalog = {'schema': 1, 'modules': {'feature': {'paths': [], 'prefixes': []}},
                        'shared_fork_paths': [self.row['path']]}
        self.record = {**self.row, 'consumers': ['feature caller'], 'blocks': ['operation'],
                       'necessity': 'Reviewed integration', 'removal_hazard': 'Caller fails',
                       'primary_module': 'native', 'module_relations': ['feature', 'native']}
        self.semantic = {'upstream_sha': self.snapshot['upstream_sha'],
                         'runtime_fingerprint': self.snapshot['runtime_fingerprint'],
                         'files': [self.record]}
        self.repo = unittest.mock.Mock()
        self.repo.commit.return_value = self.head
        self.repo.tree.return_value = {'synthetic': ('100644', 'd' * 40)}
        self.repo.text_from_tree.side_effect = lambda tree, path: json.dumps(
            self.catalog if path == source_size.CATALOG else self.semantic).encode()

    def validate(self):
        with patch.object(source_size, 'verify', return_value=self.snapshot):
            return ownership_map.validate(self.repo, 'HEAD')

    def test_complete_evidence_and_configurable_modules(self):
        self.assertEqual(self.validate()['status'], 'VERIFIED')
        self.catalog['semantic_map'] = 'review/shared.json'
        self.assertEqual(self.validate()['shared_changed_files'], 1)

    def test_baseline_runtime_and_file_fact_drift_fail(self):
        for key, value in [('upstream_sha', 'f' * 40), ('runtime_fingerprint', 'changed')]:
            with self.subTest(key=key):
                original = self.semantic[key]
                self.semantic[key] = value
                with self.assertRaises(ValueError):
                    self.validate()
                self.semantic[key] = original
        self.record['lines'] = 99
        with self.assertRaisesRegex(ValueError, 'Stale ownership'):
            self.validate()

    def test_missing_duplicate_or_unknown_ownership_fails(self):
        for files in [[], [self.record, self.record]]:
            self.semantic['files'] = files
            with self.assertRaisesRegex(ValueError, 'Missing, duplicate or stale'):
                self.validate()
        self.semantic['files'] = [self.record]
        self.record['module_relations'] = ['unknown']
        with self.assertRaisesRegex(ValueError, 'semantic consumers'):
            self.validate()
        self.record['module_relations'] = ['native']
        self.record['necessity'] = ''
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            self.validate()

    def test_unsafe_map_path_and_concurrent_changes_fail(self):
        self.catalog['semantic_map'] = '../secret.json'
        with self.assertRaisesRegex(ValueError, 'Invalid semantic map'):
            self.validate()
        self.catalog.pop('semantic_map')
        self.repo.commit.side_effect = [self.head, 'e' * 40]
        with self.assertRaisesRegex(ValueError, 'changed during'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
