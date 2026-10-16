"""Check language inheritance at actual native and external entrypoints."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import agent_batch
import orchestration
import worker_context
import workspace
from language_policy import PRIMARY_INSTRUCTIONS, WORKER_INSTRUCTIONS


class LanguageInheritanceTests(unittest.TestCase):
    def test_primary_and_role_drift_without_changing_parent_model(self):
        config = tomllib.loads(workspace.configuration('python'))
        self.assertEqual(config['developer_instructions'], PRIMARY_INSTRUCTIONS)
        self.assertNotIn('model', config)
        self.assertNotIn('model_reasoning_effort', config)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(workspace.ROOT/'.codex/agents', root/'.codex/agents')
            shutil.copytree(workspace.ROOT/'.agents/skills', root/'.agents/skills')
            for name in ('.agents/CODEX_PACK.md',):
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture authority')
            with patch.object(workspace, 'ROOT', root):
                self.assertEqual(workspace.validate()['roles'], 11)
                role = root/'.codex/agents/mu_reviewer.toml'
                role.write_text(role.read_text().replace(WORKER_INSTRUCTIONS, 'Answer the coordinator in Russian.'))
                with self.assertRaisesRegex(RuntimeError, 'language policy mismatch'):
                    workspace.validate()

    def test_generated_isolated_worker_preserves_scope_and_english(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            repo = root/'repo'; repo.mkdir()
            queue = root/'queue'; queue.mkdir()
            (repo/'go.mod').write_text('module github.com/xtls/xray-core\n')
            binary = root/'bin'/('gopls.exe' if worker_context.os.name == 'nt' else 'gopls')
            binary.parent.mkdir(); binary.write_bytes(b'fixture')
            def git(command, **kwargs):
                args = command[command.index('-C')+2:]
                if args == ['rev-parse', '--show-toplevel']: return str(repo)
                if args[:2] == ['remote', 'get-url']: return str(queue)
                if args == ['remote']: return 'origin'
                if args == ['rev-parse', 'base^{commit}']: return 'a'*40
                return ''
            with patch.object(worker_context.subprocess, 'check_output', side_effect=git):
                worker_context.setup(repo, 'base', str(queue), root)
            config = tomllib.loads((repo/'.codex/config.toml').read_text())
            guidance = config['developer_instructions']
            self.assertTrue(guidance.startswith(WORKER_INSTRUCTIONS))
            self.assertIn('never publish to GitHub or spawn nested workers', guidance)
            self.assertIn('.local/workspace/worker.json', guidance)
            self.assertFalse(config['agents']['enabled'])

    def test_external_packets_keep_literal_evidence_and_result_envelope(self):
        body = 'Inspect this literal source quotation: "ошибка пакета".'
        task = {'key': 'one', 'kind': 'review', 'title': 'One owner', 'body': body, 'inputs': ['source']}
        packet = {'batch_id': 'english-test', 'jobs': [task]}
        job = agent_batch.planned_jobs(packet, {'linux': '/frozen', 'source_head': 'a'*40})[0]
        self.assertTrue(job['body'].startswith(WORKER_INSTRUCTIONS))
        self.assertIn(body, job['body'])
        self.assertIn('status: DONE', job['body'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'task.json'; path.write_text(json.dumps(task))
            result = SimpleNamespace(returncode=0, stderr=b'', stdout=b'{"id":"fixture"}')
            with patch.object(orchestration.subprocess, 'run', return_value=result) as invoke, \
                    contextlib.redirect_stdout(io.StringIO()):
                orchestration.dispatch({'distribution': 'fixture', 'user': 'fixture', 'city': '/city'}, path)
            sent = invoke.call_args.kwargs['input'].decode()
            self.assertIn(WORKER_INSTRUCTIONS, sent)
            self.assertIn(body, sent)


if __name__ == '__main__':
    unittest.main()
