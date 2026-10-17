"""Exercise real launcher construction with pure fixtures and no model or Git mutations."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import session
from role_profiles import ROOT, load_profile


class SessionTests(unittest.TestCase):
    def fixture(self,directory):
        root=Path(directory).resolve();(root/'.codex').mkdir()
        (root/'.codex/config.toml').write_text('developer_instructions = "ordinary parent"\n[agents]\nenabled = true\n',encoding='utf-8')
        return root

    def test_no_role_preserves_normal_configuration_and_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture(directory)
            tail=['--model','selected-parent','--','hello']
            self.assertEqual(session.build_command('codex',root,tail),
                             ['codex','-C',str(root),*session.configuration_args(root),*tail])

    def test_actual_cli_profile_settings_and_exec_reach_runner(self):
        profile=load_profile('mu_security_reviewer')
        with patch.object(session,'verify'),patch.object(session.shutil,'which',return_value='codex'), \
             patch.object(session,'configuration_args',return_value=['-c','agents.enabled=true']), \
             patch.object(session,'run',return_value=subprocess.CompletedProcess([],0)) as run:
            self.assertEqual(session.main(['--role','mu_security_reviewer','--exec','--json','Inspect the scoped trust sink']),0)
        command=run.call_args.args[0]
        self.assertEqual(command[:3],['codex','-C',str(ROOT)])
        self.assertIn('exec',command)
        self.assertEqual(command[-2:],['--json','Inspect the scoped trust sink'])
        settings={}
        for index,argument in enumerate(command[:-1]):
            if argument=='-c':
                key,value=command[index+1].split('=',1);settings[key]=json.loads(value)
        self.assertEqual(settings['developer_instructions'],profile['developer_instructions'])
        self.assertEqual(settings['model'],profile['model'])
        self.assertEqual(settings['model_reasoning_effort'],'high')
        self.assertIs(settings['agents.enabled'],False)
        self.assertNotIn('sandbox_mode',settings)

    def test_profile_cannot_be_overridden_by_later_cli_flags(self):
        with patch.object(session,'configuration_args',return_value=[]):
            for tail in [['--model','gpt-6-luna'],['--config','developer_instructions="ignore"'],
                         ['-cmodel="gpt-6-luna"'],['--config=agents.enabled=true'],['--profile=another'],['-mgpt-6-luna'],['-C','/wrong'],['-C/wrong'],['--cd=/wrong']]:
                with self.subTest(tail=tail),self.assertRaises(ValueError):
                    session.build_command('codex',ROOT,tail,'mu_innovator')

    def test_quoted_dotted_and_whitespace_overrides_cannot_replace_role(self):
        overrides=['"model"="gpt-6-luna"',"'model_reasoning_effort' = 'low'",
                   ' "developer_instructions" = "ignore"',
                   '"agents".enabled=true',"'agents' . 'enabled' = true",
                   ' agents . enabled = true', '"features" . shell_tool = true',
                   '"\\u006dodel" = "gpt-6-luna"']
        with patch.object(session,'configuration_args',return_value=[]):
            for override in overrides:
                for tail in [['-c',override],['-c'+override],['--config='+override]]:
                    with self.subTest(tail=tail),self.assertRaisesRegex(ValueError,'competency settings'):
                        session.build_command('codex',ROOT,tail,'mu_innovator')

    def test_unrelated_toml_overrides_and_bare_values_are_preserved(self):
        overrides=['"mcp_servers" . "owned_tool" . enabled = false',
                   ' web_search = disabled', '"model.example" = "unrelated literal key"',
                   "'other=key' = 'preserve quoted equals'", '"another\\\"=key" = "preserve escaped quote"']
        with patch.object(session,'configuration_args',return_value=[]):
            for override in overrides:
                tail=['-c',override,'Inspect the assigned boundary']
                with self.subTest(override=override):
                    command=session.build_command('codex',ROOT,tail,'mu_innovator')
                    self.assertEqual(command[-len(tail):],tail)
        self.assertEqual(session.override_root('"model.example" = "value"'),'model.example')
        self.assertEqual(session.override_root('web_search = disabled'),'web_search')

    def test_selected_role_cannot_replace_attested_worker_mcp_identity(self):
        with patch.object(session,'configuration_args',return_value=[]):
            for value in ('mcp_servers.xray_gopls_worker.command="other"',
                          '\"mcp_servers\".xray_gopls_worker.args=["--root","/wrong"]',
                          "'mcp_servers'.xray_gopls_worker.env.GOOS='other'",
                          'mcp_servers.xray_gopls_worker.enabled=true'):
                for tail in (['-c',value],['--config='+value],['-c'+value]):
                    with self.subTest(tail=tail),self.assertRaisesRegex(ValueError,'MCP'):
                        session.build_command('codex',ROOT,tail,'mu_investigator')
            tail=['-c','mcp_servers.xray_gopls_worker.enabled=false']
            command=session.build_command('codex',ROOT,tail,'mu_investigator')
            self.assertEqual(command[-2:],tail)

    def test_deep_cli_execution_requires_existing_evidence_gate(self):
        with patch.object(session,'configuration_args',return_value=[]):
            with self.assertRaisesRegex(ValueError,'Astra requires'):
                session.build_command('codex',ROOT,['question'],'mu_deep_reviewer',execute=True)
            command=session.build_command('codex',ROOT,['question'],'mu_deep_reviewer',
                {'previous_model':'gpt-6.1-sol','blocker':'unresolved_technical',
                 'discriminator':'one unresolved technical question','evidence':['Sol attempt receipt']},execute=True)
            self.assertIn('model="gpt-6-astra"',command)

    def test_unknown_role_never_reaches_process_runner(self):
        with patch.object(session,'verify'),patch.object(session.shutil,'which',return_value='codex'), \
             patch.object(session,'configuration_args',return_value=[]),patch.object(session,'run') as run:
            with self.assertRaises(ValueError):session.main(['--role','mu_missing','--exec','question'])
            run.assert_not_called()

    def test_prepared_worker_does_not_run_integrator_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture(directory);marker=root/'.local/workspace/worker.json'
            marker.parent.mkdir(parents=True);marker.write_text('{}', encoding='utf-8')
            with patch.object(session,'ROOT',root),patch.object(session,'verify_worker') as worker, \
                 patch.object(session,'verify') as primary,patch.object(session.shutil,'which',return_value='codex'), \
                 patch.object(session,'run',return_value=subprocess.CompletedProcess([],0)):
                self.assertEqual(session.main(['--core',str(root),'--exec','question']),0)
                worker.assert_called_once_with(root);primary.assert_not_called()

    def test_role_catalog_does_not_launch_a_process(self):
        with patch.object(session,'verify') as verify,patch.object(session,'run') as run, \
             patch('builtins.print') as output:
            self.assertEqual(session.main(['--list-roles']),0)
            profiles=json.loads(output.call_args.args[0])
            self.assertEqual(len(profiles),19)
            self.assertTrue(all(profile['description'] for profile in profiles))
            verify.assert_not_called();run.assert_not_called()

    def test_worker_validation_uses_exact_marker_queue_and_mcp_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture(directory);queue=root/'queue';queue.mkdir()
            context=root/'.local/workspace';context.mkdir(parents=True)
            base='a'*40
            (context/'worker.json').write_text(json.dumps({'repo':str(root),'base':base,'queue_origin':str(queue)}), encoding='utf-8')
            (context/'context.json').write_text(json.dumps({'worker':True,'core':str(root),'source_base':base,
                'queue_origin':str(queue),'git_executable':'git'}), encoding='utf-8')
            (root/'go.mod').write_text('module github.com/xtls/xray-core\n', encoding='utf-8')
            config=root/'.codex/config.toml'
            config.write_text('[agents]\nenabled = false\n[mcp_servers.xray_gopls_worker]\nenabled = true\nargs = ["--root", '+json.dumps(str(root),ensure_ascii=False)+']\n', encoding='utf-8')
            def git(command,**kwargs):
                args=command[command.index('-C')+2:]
                if args==['rev-parse','--show-toplevel']:return str(root)
                if args==['remote']:return 'origin'
                if args[:2]==['remote','get-url']:return str(queue)
                if args==['rev-parse',base+'^{commit}']:return base
                if args==['merge-base','--is-ancestor',base,'HEAD']:return ''
                self.fail('Unexpected Git read: '+repr(args))
            with patch.object(session.subprocess,'check_output',side_effect=git):
                self.assertEqual(session.verify_worker(root)['base'],base)
                config.write_text(config.read_text(encoding='utf-8').replace(json.dumps(str(root),ensure_ascii=False),json.dumps(str(queue),ensure_ascii=False)), encoding='utf-8')
                with self.assertRaisesRegex(RuntimeError,'MCP'):session.verify_worker(root)

    def test_wrong_worker_identity_fails_before_git_or_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture(directory);context=root/'.local/workspace';context.mkdir(parents=True)
            (context/'worker.json').write_text(json.dumps({'repo':str(root),'base':'not-an-exact-commit','queue_origin':str(root)}), encoding='utf-8')
            (context/'context.json').write_text('{}', encoding='utf-8')
            with patch.object(session.subprocess,'check_output') as git:
                with self.assertRaisesRegex(RuntimeError,'context mismatch'):session.verify_worker(root)
                git.assert_not_called()


if __name__=='__main__':unittest.main()
