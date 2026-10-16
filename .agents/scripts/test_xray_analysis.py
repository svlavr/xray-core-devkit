"""Freshness and concurrent-refresh regressions for the checkout graph contract."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

import xray_analysis as analysis
from resource_guard import CancelledError, run as guarded_run


class GraphContractTests(unittest.TestCase):
    def test_recorded_node_precedes_path_and_explicit_override_precedes_recorded(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(analysis, 'host', return_value={'node': 'recorded-node'}), patch('shutil.which', return_value='path-node'):
            self.assertEqual(analysis.node_executable(), 'recorded-node')
            with patch.dict(os.environ, {'XRAY_ANALYSIS_NODE': 'explicit-node'}):
                self.assertEqual(analysis.node_executable(), 'explicit-node')

    def test_build_profile_matches_bundled_helpers_and_uses_recorded_executables(self):
        from package_map import build_environment
        with patch.dict(os.environ, {'GOWORK': 'inherited.work', 'CGO_ENABLED': '1'}), patch.object(analysis, 'host', return_value={'git_executable': 'recorded-git', 'go': 'recorded-go'}):
            env = analysis.build_env('android', 'selected')
            expected = build_environment('android/arm64', 'selected')
            for key in ('GOOS', 'GOARCH', 'CGO_ENABLED', 'GOWORK', 'GOFLAGS'):
                self.assertEqual(env[key], expected[key])
            self.assertEqual(env['XRAY_ANALYSIS_GIT'], 'recorded-git')
            self.assertEqual(env['XRAY_ANALYSIS_GO'], 'recorded-go')

    def test_cancelled_refresh_does_not_enter_owner_or_publish(self):
        cancelled=threading.Event();cancelled.set()
        before=(self.cache/'graph.json').read_bytes()
        with patch.object(analysis,'_refresh_graph_unlocked') as refresh:
            with self.assertRaises(CancelledError):
                analysis.refresh_graph(cancelled=cancelled)
            refresh.assert_not_called()
        self.assertEqual((self.cache/'graph.json').read_bytes(),before)

    def test_cancelled_refresh_owner_releases_lease_and_preserves_manifest(self):
        cancelled=threading.Event()
        before=(self.cache/'graph.json').read_bytes()
        def refresh(**kwargs):
            self.assertIs(kwargs['cancelled'],cancelled)
            cancelled.set()
            analysis.remaining(kwargs['deadline'],'fake analyzer',cancelled=cancelled)
        with patch.object(analysis,'graph_status',return_value={'status':'STALE'}), \
             patch.object(analysis,'_refresh_graph_unlocked',side_effect=refresh):
            with self.assertRaises(CancelledError):analysis.refresh_graph(cancelled=cancelled)
        self.assertEqual((self.cache/'graph.json').read_bytes(),before)
        with patch.object(analysis,'graph_status',return_value={'status':'STALE'}), \
             patch.object(analysis,'_refresh_graph_unlocked',return_value={'status':'CURRENT'}):
            self.assertEqual(analysis.refresh_graph()['status'],'CURRENT')

    def test_expired_total_deadline_cannot_start_a_refresh(self):
        with patch.object(analysis.time,'monotonic',return_value=10),patch.object(analysis,'_refresh_graph_unlocked') as refresh:
            with self.assertRaisesRegex(TimeoutError,'index lease'):
                analysis.refresh_graph(deadline=9)
            refresh.assert_not_called()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)
        self.state = {'repo': str(analysis.ROOT), 'head': 'new-doc-head',
                      'fingerprint': 'same-source', 'dirty': '',
                      'uncovered_go': [], 'workspace_files': []}
        index = self.cache / 'index'
        registry = self.cache / 'registry'
        index.mkdir(); registry.mkdir()
        (index / 'meta.json').write_text('{}')
        (index / 'lbug').touch()
        (registry / 'registry.json').write_text('{}')
        manifest = {**self.state, 'head': 'indexed-head',
                    'index': str(index), 'registry_home': str(registry)}
        (self.cache / 'graph.json').write_text(json.dumps(manifest))
        for mocker in [patch.object(analysis, 'cache_root', return_value=self.cache),
                       patch.object(analysis, 'source_state', side_effect=lambda **kwargs: self.state.copy())]:
            mocker.start(); self.addCleanup(mocker.stop)

    def test_document_only_head_change_reuses_matching_source(self):
        self.assertEqual(analysis.graph_status()['status'], 'CURRENT')

    def test_changed_dirty_or_uncovered_source_cannot_be_current(self):
        for change in [{'fingerprint': 'changed'}, {'dirty': ' M measurement/file.go'},
                       {'uncovered_go': ['newroot/api.go']}, {'workspace_files': ['go.work']}]:
            with self.subTest(change=change):
                before = self.state.copy()
                self.state.update(change)
                self.assertEqual(analysis.graph_status()['status'], 'STALE')
                self.state = before

    def test_missing_index_storage_cannot_be_current(self):
        (self.cache / 'index/lbug').unlink()
        self.assertEqual(analysis.graph_status()['status'], 'STALE')

    def test_parallel_clients_share_one_refresh(self):
        done = threading.Event()
        barrier = threading.Barrier(3)
        calls = []
        def status(deadline=None):
            return {'status': 'CURRENT' if done.is_set() else 'MISSING'}
        def refresh(deadline=None):
            calls.append(1)
            time.sleep(.1)
            done.set()
            return status()
        def client():
            barrier.wait(timeout=3)
            return analysis.refresh_graph()
        with patch.object(analysis, 'graph_status', side_effect=status), \
             patch.object(analysis, '_refresh_graph_unlocked', side_effect=refresh):
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                results = list(pool.map(lambda _: client(), range(3)))
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(r['status'] == 'CURRENT' for r in results))
        self.assertTrue((self.cache / 'graph-refresh.lock').is_file())

    def test_failed_refresh_releases_ownership_without_replacing_manifest(self):
        before = (self.cache / 'graph.json').read_bytes()
        with patch.object(analysis, 'graph_status', return_value={'status': 'STALE'}), \
             patch.object(analysis, '_refresh_graph_unlocked', side_effect=RuntimeError('failed')):
            with self.assertRaisesRegex(RuntimeError, 'failed'):
                analysis.refresh_graph()
        self.assertEqual((self.cache / 'graph.json').read_bytes(), before)
        with patch.object(analysis, 'graph_status', return_value={'status': 'STALE'}), \
             patch.object(analysis, '_refresh_graph_unlocked', return_value={'status': 'CURRENT'}):
            self.assertEqual(analysis.refresh_graph()['status'], 'CURRENT')


class CommittedArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name).resolve()
        self.binary = analysis.host()['git_executable']
        self.env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
        self.git('init', '--quiet')
        self.git('config', 'core.autocrlf', 'false')
        self.git('config', 'core.eol', 'lf')

    def git(self, *args, check=True):
        return guarded_run([self.binary, '--no-pager', '-c', 'core.fsmonitor=false',
            '-c', 'core.hooksPath=' + os.devnull, '-C', str(self.repo), *args],
            transient=self.repo / '.local/host/transient', env=self.env,
            stdin=subprocess.DEVNULL, capture_output=True, check=check,
            text=True, encoding='utf-8', timeout=20)

    def commit(self):
        self.git('add', '--', 'README.md', *[path for path in analysis.SOURCE_PATHS if (self.repo / path).exists()])
        self.git('-c', 'user.name=Archive Fixture', '-c', 'user.email=archive@example.invalid',
                 'commit', '--quiet', '--no-gpg-sign', '-m', 'Archive fixture')
        return self.git('rev-parse', 'HEAD').stdout.strip()

    def test_actual_archive_skips_missing_roots_and_uses_exact_revision(self):
        (self.repo / 'README.md').write_text('outside graph export\n')
        (self.repo / 'go.mod').write_text('module example.invalid/fixture\n')
        (self.repo / 'common').mkdir()
        (self.repo / 'common/api.go').write_bytes(b'package common\n')
        original = self.commit()
        # Reproduce the previous failure with actual Git, without GitNexus.
        failed = self.git('archive', '--format=zip', '--output=' + str(self.repo / 'failed.zip'), original,
                          *analysis.SOURCE_PATHS, check=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('did not match any files', failed.stderr)
        # Even roots tracked in the current HEAD must not enter an older snapshot.
        (self.repo / 'measurement').mkdir()
        (self.repo / 'measurement/api.go').write_text('package measurement\n')
        self.commit()
        with patch.object(analysis, 'ROOT', self.repo):
            roots = analysis.committed_source_paths(original, deadline=time.monotonic() + 20)
        self.assertEqual(roots, ('common', 'go.mod'))
        archive = self.repo / 'source.zip'
        self.git('archive', '--format=zip', '--output=' + str(archive), original, *roots)
        with zipfile.ZipFile(archive) as snapshot:
            self.assertEqual(set(snapshot.namelist()), {'common/', 'common/api.go', 'go.mod'})
            self.assertEqual(snapshot.read('common/api.go'), b'package common\n')
        # Exercise the real refresh archive/extraction path, stopping at the
        # analyzer boundary instead of running an indexer or manufacturing one.
        reached = []
        def execute(command, **kwargs):
            if command[0] != 'fixture-analyzer':
                return guarded_run(command, **kwargs)
            snapshot = Path(command[3])
            self.assertEqual((snapshot / 'common/api.go').read_bytes(), b'package common\n')
            self.assertFalse((snapshot / 'measurement').exists())
            self.assertFalse((snapshot / 'README.md').exists())
            reached.append(snapshot)
            return subprocess.CompletedProcess(command, 1, '', 'fixture stops before indexing')
        before = {'repo': str(self.repo), 'head': original, 'fingerprint': 'fixture',
                  'dirty': '', 'uncovered_go': [], 'workspace_files': []}
        with patch.object(analysis, 'ROOT', self.repo), \
             patch.object(analysis, 'cache_root', return_value=self.repo / '.local/graph-cache'), \
             patch.object(analysis, 'graph_status', return_value={'status': 'MISSING', 'source': before}), \
             patch.object(analysis, 'node_executable', return_value='fixture-analyzer'), \
             patch.object(analysis, 'guarded_run', side_effect=execute):
            with self.assertRaisesRegex(RuntimeError, 'Graph failed'):
                analysis._refresh_graph_unlocked()
        self.assertEqual(len(reached), 1)
        self.assertFalse((self.repo / '.local/graph-cache/graph.json').exists())

    def test_no_covered_roots_refuses_unscoped_archive(self):
        (self.repo / 'README.md').write_text('no graph-covered source\n')
        head = self.commit()
        with patch.object(analysis, 'ROOT', self.repo):
            with self.assertRaisesRegex(RuntimeError, 'No covered source roots'):
                analysis.committed_source_paths(head)


if __name__ == '__main__':
    unittest.main()
