"""Public audit must distinguish reserved negative fixtures from actual endpoints."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import audit
import devkit


class AuditTests(unittest.TestCase):
    def check(self, name, text):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
            (root / devkit.MANIFEST).write_text(json.dumps(devkit.build_manifest(root)), encoding='utf-8')
            return audit.audit(root)

    def test_reserved_negative_fixture_is_not_a_credential_leak(self):
        self.assertEqual(self.check('tests/test_policy.py', 'https://user:secret@example.invalid')['status'], 'PASS')

    def test_nonfixture_or_nonreserved_endpoint_remains_a_finding(self):
        for name, endpoint in [('docs/SETUP.md', 'https://' + 'user:secret@example.invalid'),
                               ('tests/test_policy.py', 'https://' + 'user:secret@example.com')]:
            result = self.check(name, endpoint)
            self.assertEqual(result['status'], 'REVIEW_REQUIRED')
            self.assertNotIn('secret', json.dumps(result))

    def test_personal_profile_path_is_reported_without_its_content(self):
        text = 'C:' + '/Users/' + 'synthetic-user/file'
        result = self.check('docs/SETUP.md', text)
        self.assertEqual(result['findings'][0]['kind'], 'personal-profile-path')
        self.assertNotIn('synthetic-user', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
