"""Protect generated worker settings from alias writes and semantic-tool drift."""
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
import subprocess
import shutil
import json
from mcp_backend import Backend
from unittest.mock import patch
import worker_context


class WorkerGuardTests(unittest.TestCase):
    def test_worker_context_has_only_local_queue_and_public_scope_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();repo=root/'repo';repo.mkdir()
            queue=root/'queue.git';queue.mkdir();tools=root/'tools';(tools/'bin').mkdir(parents=True)
            (tools/'bin'/('gopls.exe' if os.name=='nt' else 'gopls')).write_bytes(b'synthetic tool')
            (repo/'go.mod').write_text('module github.com/xtls/xray-core\n')
            def git(command,**kwargs):
                args=command[command.index('-C')+2:]
                if args==['rev-parse','--show-toplevel']:return str(repo)
                if args[:2]==['remote','get-url']:return str(queue)
                if args==['remote']:return 'origin'
                if args==['rev-parse','base^{commit}']:return 'a'*40
                return ''
            with patch.object(worker_context.subprocess,'check_output',side_effect=git):
                result=worker_context.setup(repo,'base',str(queue),tools)
            self.assertEqual(result['status'],'WORKER_CONFIGURED')
            marker=json.loads((repo/'.local/workspace/worker.json').read_text())
            self.assertEqual(marker['queue_origin'],str(queue))
            self.assertEqual(marker['base'],'a'*40)
            guidance=(repo/'.codex/config.toml').read_text()
            self.assertIn('docs/PROJECT_SCOPE.md',guidance)
            self.assertNotIn('.private',guidance)
            self.assertIn('enabled = false',guidance)
            self.assertIn('never publish to GitHub',guidance)

    def test_installed_adapter_dependency_uses_worker_owned_scratch(self):
        binary=Path(os.environ['XRAY_TEST_GOPLS']) if os.environ.get('XRAY_TEST_GOPLS') else Path(shutil.which('gopls') or '__missing_gopls__')
        if not binary.is_file():self.skipTest('Pinned gopls unavailable')
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);installed=base/'installed/lib/mu-runtime';installed.mkdir(parents=True)
            root=base/'worker';root.mkdir();(root/'go.mod').write_text('module example.test/worker\n\ngo 1.25\n')
            for name in ['go_mcp.py','resource_guard.py']:shutil.copyfile(Path(__file__).with_name(name),installed/name)
            backend=Backend([sys.executable,str(installed/'go_mcp.py'),'--binary',str(binary),'--root',str(root)],root,
                dict(os.environ,GOWORK='off',GOMAXPROCS='2'),subprocess.DEVNULL,timeout=20)
            try:
                response=backend.call({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'go_workspace','arguments':{}}})
                self.assertNotIn('error',response)
                self.assertIn(str(root),json.dumps(response).replace('\\\\','\\'))
                self.assertTrue(list((root/'.local/host/transient').glob('run-*/owner.json')))
                self.assertFalse((base/'installed/.local').exists())
            finally:backend.close()
            self.assertFalse(list((root/'.local/host/transient').glob('run-*/owner.json')))

    def test_worker_marker_hardlink_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();repo=root/'repo';repo.mkdir()
            queue=root/'queue';queue.mkdir()
            (repo/'go.mod').write_text('module github.com/xtls/xray-core\n')
            marker=repo/'.local/workspace/worker.json';marker.parent.mkdir(parents=True)
            outside=root/'outside.txt';outside.write_text('preserve me')
            os.link(outside,marker)
            def git(command,**kwargs):
                args=command[command.index('-C')+2:]
                if args==['rev-parse','--show-toplevel']:return str(repo)
                if args[:2]==['remote','get-url']:return str(queue)
                if args==['remote']:return 'origin'
                if args==['rev-parse','base^{commit}']:return 'a'*40
                return ''
            with patch.object(worker_context.subprocess,'check_output',side_effect=git):
                with self.assertRaisesRegex(RuntimeError,'alias'):
                    worker_context.setup(repo,'base',str(queue),root)
            self.assertEqual(outside.read_text(),'preserve me')
            self.assertFalse((marker.parent/'context.json').exists())

    def test_new_gopls_version_cannot_use_old_line_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'go.mod').write_text('module test\n')
            script=Path(__file__).with_name('go_mcp.py')
            argv=[str(script),'--binary',sys.executable,'--root',str(root)]
            with patch.object(sys,'argv',argv), \
                 patch('resource_guard.run',return_value=subprocess.CompletedProcess([],0,'golang.org/x/tools/gopls v0.24.0\n','')), \
                 patch('subprocess.Popen') as spawn:
                with self.assertRaisesRegex((SystemExit,RuntimeError),'requires gopls v0.23.0'):
                    runpy.run_path(str(script),run_name='__main__')
                spawn.assert_not_called()


if __name__=='__main__':
    unittest.main()
