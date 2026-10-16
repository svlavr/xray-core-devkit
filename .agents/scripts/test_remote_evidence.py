"""Network failure, stale evidence and local HEAD must remain distinguishable."""
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from remote_evidence import observe,reuse

REF='refs/heads/example'
SHA='a'*40


class RemoteEvidenceTests(unittest.TestCase):
    def call(self,result,expected=SHA,remote='origin'):
        with patch('remote_evidence.workspace.git',return_value='https://example.invalid/owner/source.git'):
            return observe(remote,REF,expected,runner=lambda *a,**kw:result)

    def test_configured_alias_and_invalid_remote_or_ref(self):
        r=self.call(SimpleNamespace(returncode=0,stdout=SHA+'\t'+REF+'\n',stderr=''),remote='team-fork')
        self.assertEqual(r['status'],'LIVE')
        for remote,ref in [('--upload-pack=bad',REF),('https://example.invalid/repo',REF),
                           ('origin','refs/heads/../bad'),('origin','refs/heads/bad.lock')]:
            with self.subTest(remote=remote,ref=ref),self.assertRaises(ValueError):
                observe(remote,ref)

    def test_live_exact_identity(self):
        r=self.call(SimpleNamespace(returncode=0,stdout=SHA+'\t'+REF+'\n',stderr=''))
        self.assertEqual((r['status'],r['sha'],r['matches_expected']),('LIVE',SHA,True))

    def test_failure_never_becomes_local_expected_sha(self):
        r=self.call(SimpleNamespace(returncode=128,stdout='',stderr='connection failed'))
        self.assertEqual(r['status'],'UNAVAILABLE');self.assertIsNone(r['sha'])
        self.assertIsNone(r['matches_expected']);self.assertIn('connection failed',r['error'])

    def test_timeout_and_wrong_ref_stay_unavailable(self):
        with patch('remote_evidence.workspace.git',return_value='url'):
            def timeout(*a,**kw):raise subprocess.TimeoutExpired('git',35)
            self.assertEqual(observe('origin',REF,SHA,runner=timeout)['status'],'UNAVAILABLE')
        self.assertEqual(self.call(SimpleNamespace(returncode=0,stdout=SHA+'\trefs/heads/other\n',stderr=''))['status'],'UNAVAILABLE')

    def test_live_mismatch_is_not_hidden_and_reuse_keeps_time(self):
        for remote in ('origin','public'):
            r=self.call(SimpleNamespace(returncode=0,stdout='b'*40+'\t'+REF+'\n',stderr=''),remote=remote)
            self.assertFalse(r['matches_expected']);self.assertEqual(r['sha'],'b'*40)
        old=reuse(r,'earlier-receipt.json')
        self.assertEqual(old['observed_at'],r['observed_at']);self.assertEqual(old['status'],'REUSED')
        with self.assertRaises(ValueError):reuse({'status':'UNAVAILABLE'},'failed.json')

    def test_missing_remote_configuration_produces_unavailable_receipt(self):
        with patch('remote_evidence.workspace.git',side_effect=RuntimeError('No remote configured')):
            r=observe('origin',REF,SHA)
        self.assertEqual(r['status'],'UNAVAILABLE');self.assertIsNone(r['sha'])
        self.assertIn('No remote configured',r['error'])


if __name__=='__main__':unittest.main()
