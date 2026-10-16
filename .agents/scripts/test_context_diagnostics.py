import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from context_diagnostics import inspect


class ContextEvidenceTests(unittest.TestCase):
    def test_runtime_and_ui_counts_stay_distinct_and_prompt_is_not_emitted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.codex').mkdir()
            (root / '.codex/config.toml').write_text(
                'model_context_window=872000\nmodel_auto_compact_token_limit=662720\n'
                'model_auto_compact_token_limit_scope="total"\n')
            rollout = root / 'rollout.jsonl'
            rollout.write_text('\n'.join(json.dumps(item) for item in [
                {'timestamp': '2026-10-10T18:00:00Z', 'type': 'turn_context',
                 'payload': {'model': 'gpt-6.1-sol', 'effort': 'high', 'turn_id': 'turn', 'prompt': 'PRIVATE'}},
                {'timestamp': '2026-10-10T18:03:32.996Z', 'type': 'event_msg',
                 'payload': {'type': 'token_count', 'info': {'model_context_window': 828400,
                    'last_token_usage': {'total_tokens': 477791}, 'secret': 'PRIVATE'}}},
                {'timestamp': '2026-10-10T18:03:32.998Z', 'type': 'turn_context',
                 'payload': {'model': 'gpt-6-astra', 'effort': 'high', 'turn_id': 'new-turn'}},
                {'timestamp': '2026-10-10T18:03:32.999Z', 'type': 'event_msg',
                 'payload': {'type': 'token_count', 'info': {'last_token_usage': {'total_tokens': 100}}}},
                {'timestamp': '2026-10-10T18:06:00Z', 'type': 'compacted', 'payload': {'message': 'PRIVATE'}}
            ]))
            with closing(sqlite3.connect(root / 'state_5.sqlite', isolation_level=None)) as db:
                db.execute('CREATE TABLE threads(id,cwd,rollout_path,model,reasoning_effort)')
                db.execute('INSERT INTO threads VALUES(?,?,?,?,?)', ('thread', str(root), str(rollout), 'gpt-6.1-sol', 'high'))
            with closing(sqlite3.connect(root / 'logs_2.sqlite', isolation_level=None)) as db:
                db.execute('CREATE TABLE logs(id,ts,ts_nanos,thread_id,target,feedback_log_body)')
                db.execute('INSERT INTO logs VALUES(?,?,?,?,?,?)', (1, 1791655412, 997581300, 'thread',
                    'codex_core::session::turn', 'post sampling token usage turn_id=turn total_usage_tokens=676207 '
                    'auto_compact_scope_tokens=676207 auto_compact_scope_limit=Some(662720) '
                    'auto_compact_limit_scope=Total full_context_window_limit=Some(828400) '
                    'full_context_window_limit_reached=false token_limit_reached=true PRIVATE'))
            result = inspect(root, root, 'thread', now=1791655500)
            self.assertTrue(result['observed_limit_matches_generated'])
            self.assertEqual(result['counter_difference'], 198416)
            self.assertEqual(result['rollout_correlation'], 'EXACT_TURN_AND_TIME')
            self.assertEqual(result['model_at_observation']['model'], 'gpt-6.1-sol')
            self.assertNotIn('PRIVATE', json.dumps(result))
            self.assertEqual(result['server_last_request']['usage']['total_tokens'], 477791)
            with self.assertRaisesRegex(ValueError, 'another project'):
                inspect(root, root / 'foreign', 'thread', now=1791655500)
            with closing(sqlite3.connect(root / 'logs_2.sqlite', isolation_level=None)) as db:
                db.execute("UPDATE logs SET feedback_log_body=replace(feedback_log_body,'turn_id=turn','turn_id=other')")
            mismatch = inspect(root, root, 'thread', now=1791655500)
            self.assertIsNone(mismatch['server_last_request'])
            self.assertNotIn('counter_difference', mismatch)
            with closing(sqlite3.connect(root / 'logs_2.sqlite', isolation_level=None)) as db:
                db.execute('DELETE FROM logs')
            self.assertIsNone(inspect(root, root, 'thread', now=1791655500)['runtime_observation'])


if __name__ == '__main__':
    unittest.main()
