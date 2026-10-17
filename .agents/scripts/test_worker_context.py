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
import tomllib
from mcp_backend import Backend
from unittest.mock import patch
import workspace
import worker_context


class WorkerGuardTests(unittest.TestCase):
    def test_worker_context_has_only_local_queue_and_public_scope_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();repo=root/'repo-\U0001f680';repo.mkdir()
            queue=root/'queue.git';queue.mkdir();tools=root/'tools-\U0001f680';(tools/'bin').mkdir(parents=True)
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
            guidance=(repo/'.codex/config.toml').read_text(encoding='utf-8')
            parsed=tomllib.loads(guidance)
            self.assertEqual(parsed['mcp_servers']['xray_gopls_worker']['args'],[
                str(Path(worker_context.__file__).with_name('go_mcp.py').resolve()),'--binary',
                str(tools/'bin'/('gopls.exe' if os.name=='nt' else 'gopls')),'--root',str(repo)])
            self.assertEqual(parsed['mcp_servers']['xray_gopls_worker']['args'][-1],str(repo))
            self.assertIn(str(tools),parsed['mcp_servers']['xray_gopls_worker']['args'][2])
            self.assertFalse(parsed['agents']['enabled'])
            self.assertNotIn('model',parsed)
            self.assertEqual(set(parsed['mcp_servers']),{'xray_gopls_worker','context7','grep_app','exa_public_research'})
            self.assertEqual(parsed['mcp_servers']['context7'],{
                'enabled':True,'url':'https://mcp.context7.com/mcp',
                'startup_timeout_sec':60,'tool_timeout_sec':60})
            self.assertEqual(parsed['mcp_servers']['grep_app'],{
                'enabled':True,'default_tools_approval_mode':'auto','url':'https://mcp.grep.app',
                'enabled_tools':['searchGitHub'],'startup_timeout_sec':60,'tool_timeout_sec':60})
            self.assertEqual(parsed['mcp_servers']['exa_public_research'],{
                'enabled':True,
                'url':'https://mcp.exa.ai/mcp?tools=web_search_exa,web_fetch_exa',
                'enabled_tools':['web_search_exa','web_fetch_exa'],
                'startup_timeout_sec':45,'tool_timeout_sec':45})
            self.assertIn('Exa web_search_exa requires query and objective',parsed['developer_instructions'])
            self.assertIn('never send private source, contracts, credentials or logs',parsed['developer_instructions'])
            self.assertIn('parent session permissions and approvals',parsed['developer_instructions'])
            self.assertIn('docs/PROJECT_SCOPE.md',guidance)
            self.assertNotIn('.private',guidance)
            self.assertIn('enabled = false',guidance)
            self.assertIn('never publish to GitHub',guidance)
            legacy=guidance.replace(
                '[mcp_servers.grep_app]\nenabled = true\ndefault_tools_approval_mode = "auto"',
                '[mcp_servers.grep_app]\nenabled = false\ndefault_tools_approval_mode = "deny"'
                '\nbearer_token_env_var = "OLD_SEARCH_TOKEN"\ndisabled_tools = ["searchGitHub"]')
            legacy=legacy.replace(
                '[mcp_servers.exa_public_research]\nenabled = true',
                '[mcp_servers.exa_public_research]\nenabled = false\ndefault_tools_approval_mode = "deny"'
                '\nbearer_token_env_var = "OLD_EXA_TOKEN"\ndisabled_tools = ["web_fetch_exa"]')
            (repo/'.codex/config.toml').write_text(legacy,encoding='utf-8',newline='\n')
            with patch.object(worker_context.subprocess,'check_output',side_effect=git):
                worker_context.setup(repo,'base',str(queue),tools)
            regenerated=tomllib.loads((repo/'.codex/config.toml').read_text(encoding='utf-8'))
            self.assertEqual(regenerated,parsed)

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
                self.assertTrue(any(str(root) in item.get('text','') for item in response.get('result',{}).get('content',[])))
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


    def test_explicit_mcp_layer_keeps_frozen_adapter_and_actual_source_root(self):
        config={'developer_instructions':'already combined','approval_policy':'never','sandbox_mode':'read-only',
            'mcp_servers':{'xray_gopls_worker':{'enabled':True,'command':'/usr/bin/python3',
                'args':['/frozen/.agents/scripts/go_mcp.py','--binary','/tools-'+chr(0x1f680)+'/gopls','--root','/worker-'+chr(0x1f680)],
                'env':{'GOOS':'linux','GOFLAGS':'-mod=readonly'}},
                'server.with.dot':{'enabled':False}}}
        args=worker_context.scoped_mcp_args(config)
        overrides=[args[index+1] for index,item in enumerate(args) if item=='-c']
        self.assertTrue(all(value.startswith('mcp_servers.') for value in overrides))
        self.assertIn('mcp_servers.xray_gopls_worker.enabled=true',overrides)
        self.assertIn('mcp_servers."server.with.dot".enabled=false',overrides)
        effective=tomllib.loads('\n'.join(args[index+1] for index,item in enumerate(args) if item=='-c'))
        self.assertEqual(effective,{'mcp_servers':config['mcp_servers']})
        self.assertEqual(effective['mcp_servers']['xray_gopls_worker']['args'],config['mcp_servers']['xray_gopls_worker']['args'])


    def test_qualified_public_research_preserves_worker_root_and_parent_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();repo=root/'worker root';repo.mkdir()
            queue=root/'local queue';queue.mkdir()
            tools=root/'worker tools';(tools/'bin').mkdir(parents=True)
            binary=tools/'bin'/('gopls.exe' if os.name=='nt' else 'gopls')
            binary.write_bytes(b'fixture tool')
            (repo/'go.mod').write_text('module github.com/xtls/xray-core\n')
            def git(command,**kwargs):
                self.assertEqual(command[command.index('-C')+1],str(repo))
                args=command[command.index('-C')+2:]
                if args==['rev-parse','--show-toplevel']:return str(repo)
                if args[:2]==['remote','get-url']:return str(queue)
                if args==['remote']:return 'origin'
                if args==['rev-parse','base^{commit}']:return 'a'*40
                return ''
            with patch.object(worker_context.subprocess,'check_output',side_effect=git):
                result=worker_context.setup(repo,'base',str(queue),tools)
            self.assertEqual(result['root'],str(repo))
            context=json.loads((repo/'.local/workspace/context.json').read_text())
            marker=json.loads((repo/'.local/workspace/worker.json').read_text())
            self.assertEqual(context['core'],str(repo))
            self.assertEqual(context['analysis_tools'],str(tools))
            self.assertEqual(context['source_base'],marker['base'])
            self.assertEqual(marker,{'base':'a'*40,'repo':str(repo),'queue_origin':str(queue)})
            config=tomllib.loads((repo/'.codex/config.toml').read_text(encoding='utf-8'))
            guidance=config['developer_instructions']
            for constraint in (
                'Remote Context7, grep.app and exa_public_research receive public identifiers/questions/URLs only;',
                'never send private source, contracts, credentials or logs.',
                'Exa web_search_exa requires query and objective',
                'web_fetch_exa takes urls',
                'model-generated summaries and search results do not prove tested behavior or implementation completeness.',
                'Do not invoke research agents or nested workers;',
                'return deciding evidence and explicit unknowns to the coordinator.'):
                self.assertIn(constraint,guidance)
            self.assertEqual(config['mcp_servers']['exa_public_research'],{
                'enabled':True,'url':'https://mcp.exa.ai/mcp?tools=web_search_exa,web_fetch_exa',
                'enabled_tools':['web_search_exa','web_fetch_exa'],
                'startup_timeout_sec':45,'tool_timeout_sec':45})
            self.assertEqual(config['mcp_servers']['xray_gopls_worker']['args'],[
                str(Path(worker_context.__file__).with_name('go_mcp.py').resolve()),
                '--binary',str(binary),'--root',str(repo)])
            self.assertFalse(config['agents']['enabled'])
            for key in ('model','model_reasoning_effort','approval_policy','sandbox_mode'):
                self.assertNotIn(key,config)
            self.assertNotIn('exa_public_research',tomllib.loads(workspace.configuration('python'))['mcp_servers'])



if __name__=='__main__':
    unittest.main()
