"""Read bounded local context evidence without exposing prompts or credentials."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import tomllib

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ('total_usage_tokens', 'auto_compact_scope_tokens',
          'auto_compact_scope_limit', 'auto_compact_limit_scope',
          'auto_compact_window_prefill_tokens', 'full_context_window_limit',
          'full_context_window_limit_reached', 'token_limit_reached')
SETTINGS = ('model_context_window', 'model_auto_compact_token_limit',
            'model_auto_compact_token_limit_scope')


def normalized(path):
    return str(path).removeprefix('\\\\?\\').replace('\\', '/').rstrip('/').casefold()


def connect(path):
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True,
                                timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def usage_fields(body):
    result = {}
    for key in FIELDS:
        match = re.search(r'\b' + key + r'=(?:Some\()?'
                          r'(true|false|None|Total|BodyAfterPrefix|\d+)\)?', body)
        if match:
            value = match.group(1)
            result[key] = (int(value) if value.isdigit() else
                           value == 'true' if value in ('true', 'false') else
                           None if value == 'None' else value)
    return result


def runtime_turn(body):
    match = re.search(r'\bpost sampling token usage\s+turn_id=([A-Za-z0-9_-]+)\b', body)
    return match.group(1) if match else None


def rollout_evidence(path, trigger_time, turn_id=None):
    """Only scan a bounded tail and retain whitelisted accounting fields."""
    counts, compactions, model = [], [], None
    with path.open('rb') as handle:
        size = handle.seek(0, 2)
        start = max(0, size - 16 * 1024 * 1024)
        handle.seek(start)
        data = handle.read(size - start)
        truncated = start > 0
        if truncated:
            data = data.split(b'\n', 1)[-1] if b'\n' in data else b''
        for line in data.splitlines():
            if len(line) > 2 * 1024 * 1024:
                continue
            try:
                item = json.loads(line)
                stamp = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')).timestamp()
                payload = item.get('payload', {})
                if item.get('type') == 'turn_context':
                    if trigger_time is None or stamp <= trigger_time:
                        model = {key: payload.get(key) for key in ('model', 'effort', 'turn_id')}
                elif item.get('type') == 'compacted':
                    compactions.append({'timestamp': item['timestamp']})
                elif item.get('type') == 'event_msg' and payload.get('type') == 'token_count':
                    info = payload.get('info') or {}
                    usage = info.get('last_token_usage') or {}
                    if usage and (trigger_time is None or stamp <= trigger_time):
                        counts.append({'timestamp': item['timestamp'],
                                       'turn_id': (model or {}).get('turn_id'),
                                       'model_context_window': info.get('model_context_window'),
                                       'usage': {key: usage[key] for key in
                                                 ('input_tokens', 'output_tokens',
                                                  'reasoning_output_tokens', 'total_tokens')
                                                 if key in usage}})
            except (ValueError, KeyError, TypeError):
                continue
    if turn_id and (model or {}).get('turn_id') != turn_id:
        model = None
    turn = turn_id or (model or {}).get('turn_id')
    matching = [value for value in counts if not turn or value['turn_id'] == turn]
    return {'model_at_observation': model, 'server_last_request': matching[-1] if matching else None,
            'rollout_correlation': 'EXACT_TURN_AND_TIME' if turn_id and matching else
                                   'NO_MATCH' if turn_id else 'TEMPORAL_ONLY',
            'recent_compactions': compactions[-8:], 'tail_truncated': truncated}


def inspect(home, root, thread_id, hours=24, now=None):
    if not 1 <= hours <= 168:
        raise ValueError('Observation window must be 1..168 hours')
    with closing(connect(home / 'state_5.sqlite')) as db:
        row = db.execute('SELECT id,cwd,rollout_path,model,reasoning_effort FROM threads WHERE id=?',
                         (thread_id,)).fetchone()
    if row is None or normalized(row['cwd']) != normalized(root):
        raise ValueError('Thread is absent or belongs to another project root')
    now = time.time() if now is None else now
    with closing(connect(home / 'logs_2.sqlite')) as db:
        rows = db.execute(
            "SELECT id,ts,ts_nanos,feedback_log_body FROM logs WHERE thread_id=? AND ts BETWEEN ? AND ? "
            "AND target='codex_core::session::turn' "
            "AND feedback_log_body LIKE '%post sampling token usage%' "
            'ORDER BY ts DESC,ts_nanos DESC,id DESC LIMIT 200',
            (thread_id, int(now - hours * 3600), int(now))).fetchall()
    samples = [{'log_id': value['id'],
                'timestamp': datetime.fromtimestamp(value['ts'] + value['ts_nanos'] / 1e9, timezone.utc).isoformat(),
                'epoch': value['ts'] + value['ts_nanos'] / 1e9,
                'ts_nanos': value['ts_nanos'], 'turn_id': runtime_turn(value['feedback_log_body']),
                **usage_fields(value['feedback_log_body'])} for value in rows]
    triggers = [value for value in samples if value.get('token_limit_reached') is True
                or value.get('full_context_window_limit_reached') is True]
    observation = triggers[0] if triggers else samples[0] if samples else None
    evidence = rollout_evidence(Path(row['rollout_path']), observation['epoch'] if observation else None,
                                observation.get('turn_id') if observation else None)
    config = tomllib.loads((root / '.codex/config.toml').read_text(encoding='utf-8'))
    configured = {key: config.get(key) for key in SETTINGS}
    catalog_path = home / 'models_cache.json'
    models = {}
    if catalog_path.is_file():
        catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
        names = {'gpt-6-astra', 'gpt-6.1-sol', 'gpt-6-luna', row['model']}
        for item in catalog.get('models', []):
            if item.get('slug') in names:
                models[item['slug']] = {key: item.get(key) for key in
                    ('context_window', 'max_context_window', 'effective_context_window_percent')}
    result = {'thread_id': thread_id, 'project_root': str(root),
              'thread_metadata_model': row['model'],
              'thread_metadata_effort': row['reasoning_effort'],
              'generated_project_settings': configured,
              'local_catalog_capabilities': models,
              'runtime_observation': observation,
              'observation_is_threshold_trigger': bool(triggers),
              'server_matching_rule': 'Latest token_count at/before exact runtime timestamp, in the observed rollout turn when known; delayed counts remain unmatched',
              **evidence}
    if observation:
        limit = observation.get('auto_compact_scope_limit')
        expected = configured.get('model_auto_compact_token_limit')
        result['observed_limit_matches_generated'] = limit == expected if limit is not None and expected is not None else None
        scope = observation.get('auto_compact_limit_scope')
        result['observed_scope_matches_generated'] = (
            {'Total': 'total', 'BodyAfterPrefix': 'body_after_prefix'}.get(scope)
            == configured.get('model_auto_compact_token_limit_scope')) if scope else None
        server = (evidence['server_last_request'] or {}).get('usage', {}).get('total_tokens')
        full = observation.get('full_context_window_limit')
        runtime = observation.get('auto_compact_scope_tokens')
        if full and runtime is not None:
            result['runtime_scope_percent_of_usable'] = round(runtime / full * 100, 3)
        if full and server is not None:
            result['server_request_percent_of_usable'] = round(server / full * 100, 3)
        if runtime is not None and server is not None and evidence['rollout_correlation'] == 'EXACT_TURN_AND_TIME':
            result['counter_difference'] = runtime - server
    result['accounting_note'] = (
        'Runtime active-context accounting and server last-request usage are distinct. '
        'Their difference does not establish a model error or a correction factor. '
        'Generated settings alone do not prove an existing session loaded them; '
        'absent runtime evidence remains unknown. A threshold observation does not '
        'prove compaction completed or exclude other compaction causes.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--thread', required=True)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--codex-home', type=Path,
                        default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    parser.add_argument('--hours', type=int, default=24)
    args = parser.parse_args()
    print(json.dumps(inspect(args.codex_home, args.root.resolve(), args.thread, args.hours), indent=2))
