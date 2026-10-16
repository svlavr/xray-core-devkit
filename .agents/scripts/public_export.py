"""Prepare, verify and publish a committed-source export without private ancestry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from workspace import ROOT, FLAGS, git_executable, host_target, repository_guard

MANIFEST = '.agents/public-export.json'
PRIVATE_DIRS = {'.agents', '.codex', '.private', '.local', '.git', '.codex-remote-attachments'}
PRIVATE_FILES = {'agents.md', 'agents.override.md', '.env'}

def run(*args, data=None, index=None, timeout=25, allowed=(0,)):
    env = os.environ.copy()
    for name in ['GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR',
                 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES']:
        env.pop(name, None)
    if index is not None:
        env['GIT_INDEX_FILE'] = str(index)
    command = [git_executable(), '--no-pager', '--no-optional-locks', '-c', 'core.fsmonitor=false',
               '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(ROOT), *args]
    result = subprocess.run(command, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, creationflags=FLAGS, timeout=timeout)
    time.sleep(0.05)
    if result.returncode not in allowed:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace').strip() or 'Git operation failed')
    return result.stdout

def oid(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}', value):
        raise RuntimeError('Expected an exact commit/object SHA')
    return value

def is_private(path):
    return any(part.casefold() in PRIVATE_DIRS or part.casefold() in PRIVATE_FILES
               or part.casefold().startswith('.env.') for part in path.split('/'))

def safe_path(path):
    if not isinstance(path, str) or not path or '\\' in path or ':' in path or any(ord(c) < 32 for c in path):
        raise RuntimeError('Invalid export path')
    if any(part in ('', '.', '..') or part.endswith((' ', '.')) for part in path.split('/')):
        raise RuntimeError('Invalid export path components')
    if is_private(path):
        raise RuntimeError('Private path forbidden in public manifest: ' + path)

def entries(commit):
    result = {}
    for record in run('ls-tree', '-r', '-z', oid(commit)).split(b'\0'):
        if not record:
            continue
        header, name = record.split(b'\t', 1)
        mode, kind, blob = header.decode('ascii').split()
        result[name.decode('utf-8')] = (mode, kind, blob)
    return result

def historical_entries(manifest):
    """Exact retired public blobs may occur in history, never in a new export."""
    records = manifest.get('historical_only', {})
    if not isinstance(records, dict):
        raise RuntimeError('Historical export records must be a path mapping')
    live = {path.casefold() for path in manifest['paths']}
    seen, result = set(), {}
    for path, versions in records.items():
        safe_path(path)
        folded = path.casefold()
        if folded in live or folded in seen:
            raise RuntimeError('Historical path overlaps live paths or aliases another path')
        seen.add(folded)
        if not isinstance(versions, list) or not versions:
            raise RuntimeError('Historical path requires exact nonempty blob records')
        admitted = set()
        for item in versions:
            if not isinstance(item, dict) or set(item) != {'mode', 'blob'}:
                raise RuntimeError('Historical entry requires exact mode and blob')
            if item['mode'] not in ('100644', '100755'):
                raise RuntimeError('Historical symlink/submodule mode forbidden')
            entry = (item['mode'], oid(item['blob']))
            if entry in admitted:
                raise RuntimeError('Duplicate historical blob record')
            admitted.add(entry)
        result[path] = admitted
    return result


def load_manifest(source):
    raw = run('show', f'{oid(source)}:{MANIFEST}')
    manifest = json.loads(raw)
    validate_policy(manifest)
    paths = manifest['paths']
    if not isinstance(paths, list) or not paths:
        raise RuntimeError('Explicit nonempty public path allowlist required')
    for path in paths:
        safe_path(path)
    if len({p.casefold() for p in paths}) != len(paths):
        raise RuntimeError('Duplicate or case-aliased public paths')
    historical_entries(manifest)
    return manifest, hashlib.sha256(raw).hexdigest()

def validate_policy(manifest):
    """Publication authority comes from a user's committed policy, never defaults."""
    if manifest.get('schema') != 1:
        raise RuntimeError('Unsupported export manifest schema')
    oid(manifest.get('public_anchor'))
    url = manifest.get('public_url')
    if (not isinstance(url, str) or not re.fullmatch(r'https://[A-Za-z0-9.-]+(?::[0-9]+)?/[A-Za-z0-9_./-]+\.git', url)
            or any(part in ('.', '..') for part in url.split('/')[3:])):
        raise RuntimeError('Explicit HTTPS public repository .git URL required')
    for key in ('public_ref', 'anchor_ref'):
        ref = manifest.get(key)
        if (not isinstance(ref, str) or not ref.startswith('refs/heads/')
                or not re.fullmatch(r'refs/heads/[A-Za-z0-9_./-]+', ref)
                or any(part in ('', '.', '..') or part.startswith('.') or part.endswith(('.', '.lock')) for part in ref.split('/'))
                or '..' in ref or '@{' in ref):
            raise RuntimeError('Explicit exact branch ref required: ' + key)
    if not isinstance(manifest.get('ci_blobs'), dict):
        raise RuntimeError('Explicit ci_blobs object required')


def select(source_entries, manifest):
    historical_entries(manifest)
    paths = set(manifest['paths'])
    for path in paths:
        safe_path(path)
    missing = paths - source_entries.keys()
    unknown = {path for path in source_entries if path not in paths and not is_private(path)}
    if missing or unknown:
        raise RuntimeError('Manifest/source mismatch: ' + repr({'missing': sorted(missing), 'unlisted': sorted(unknown)}))
    selected = {path: source_entries[path] for path in sorted(paths)}
    for path, (mode, kind, blob) in selected.items():
        if mode not in ('100644', '100755') or kind != 'blob':
            raise RuntimeError('Symlink/submodule/non-file export forbidden: ' + path)
        oid(blob)
    active = {p for p in selected if p.startswith('.github/workflows/')}
    if active != set(manifest['ci_blobs']):
        raise RuntimeError('Every active workflow requires an explicit reviewed blob pin')
    for path, blob in manifest['ci_blobs'].items():
        if selected[path][2] != oid(blob):
            raise RuntimeError('CI changed without manifest review: ' + path)
    return selected

def destination_guard(manifest):
    validate_policy(manifest)
    public_url = manifest['public_url']
    # Refuse any applicable rule rather than interpreting Git's longest-prefix rules.
    raw = run('config', '--null', '--get-regexp', r'^url\..*\.(insteadof|pushinsteadof)$', allowed=(0, 1))
    for record in raw.split(b'\0'):
        if not record:
            continue
        _, prefix = record.split(b'\n', 1)
        if public_url.startswith(prefix.decode('utf-8')):
            raise RuntimeError('Git URL rewrite changes the configured public destination; export refused')
    if run('ls-remote', '--get-url', public_url).decode('utf-8').strip() != public_url:
        raise RuntimeError('Git URL rewrite changes the configured public destination; export refused')

def remote_head(manifest, ref=None):
    destination_guard(manifest)
    ref = ref or manifest['public_ref']
    raw = run('ls-remote', '--heads', manifest['public_url'], ref).decode('ascii').splitlines()
    if not raw:
        return None
    if len(raw) != 1 or raw[0].split()[1] != ref:
        raise RuntimeError('Unexpected remote ref response')
    return oid(raw[0].split()[0])

def public_history(candidate, source, manifest):
    anchor = oid(manifest['public_anchor'])
    run('merge-base', '--is-ancestor', anchor, oid(candidate))
    private_commits = set(run('rev-list', oid(source), '^' + anchor).decode().splitlines())
    chain = run('rev-list', '--reverse', '--parents', candidate, '^' + anchor).decode().splitlines()
    allowed_paths = set(manifest['paths']) | set(entries(anchor))
    retired = historical_entries(manifest)
    previous = anchor
    for line in chain:
        fields = line.split()
        if len(fields) != 2 or fields[1] != previous or fields[0] in private_commits:
            raise RuntimeError('Public ancestry contains a private commit, merge or unexpected parent')
        commit = fields[0]
        for path, (mode, kind, blob) in entries(commit).items():
            safe_path(path)
            if (mode not in ('100644', '100755') or kind != 'blob'
                    or (path not in allowed_paths and (mode, blob) not in retired.get(path, set()))):
                raise RuntimeError('Unreviewed path/mode in public ancestry: ' + path)
        previous = commit

def clean_source():
    # Worker copies inherit tracked policy/manifest bytes, never publication authority.
    # Treat even a dangling marker link as worker state and refuse before Git reads.
    if os.path.lexists(ROOT / '.local/workspace/worker.json'):
        raise RuntimeError('Worker checkouts cannot prepare or publish public exports')
    p = repository_guard()
    if p.get('worker'):
        raise RuntimeError('Worker checkouts cannot prepare or publish public exports')
    if p.get('public_push_mode') != 'filtered-export-only':
        raise RuntimeError('Explicit filtered-export-only project policy is required')
    if run('status', '--porcelain', '--untracked-files=all').strip():
        raise RuntimeError('Commit and review all owned work before preparing/publishing an export')
    source = oid(run('rev-parse', 'HEAD').decode().strip())
    manifest, _ = load_manifest(source)
    for key, field in [('public_url', 'public_url'), ('anchor', 'public_anchor'),
                       ('public_branch', 'public_ref')]:
        expected = p.get(key)
        if key == 'public_branch' and expected and not expected.startswith('refs/heads/'):
            expected = 'refs/heads/' + expected
        if expected and expected != manifest[field]:
            raise RuntimeError('Export manifest differs from project policy: ' + key)
    return source

def build_tree(selected):
    index = host_target('.local/export/index-' + uuid.uuid4().hex)
    index.parent.mkdir(parents=True, exist_ok=True)
    try:
        run('read-tree', '--empty', index=index)
        payload = b''.join(f'{mode} {blob}\t{path}\0'.encode('utf-8')
                           for path, (mode, _, blob) in sorted(selected.items()))
        run('update-index', '-z', '--index-info', data=payload, index=index)
        return oid(run('write-tree', index=index).decode().strip())
    finally:
        for path in [index, Path(str(index) + '.lock')]:
            host_target(path.relative_to(ROOT).as_posix()).unlink(missing_ok=True)

def validate_candidate(receipt, source):
    manifest, digest = load_manifest(source)
    anchor = manifest['public_anchor']
    if (receipt['private_sha'] != oid(source) or receipt['public_ref'] != manifest['public_ref']
            or receipt.get('public_url') != manifest['public_url']):
        raise RuntimeError('Receipt does not name the reviewed source/destination')
    if receipt['manifest_sha256'] != digest:
        raise RuntimeError('Manifest provenance mismatch')
    selected = select(entries(source), manifest)
    candidate = oid(receipt['public_sha'])
    if entries(candidate) != selected:
        raise RuntimeError('Public tree differs from committed allowlisted source')
    if run('rev-parse', candidate + '^{tree}').decode().strip() != receipt['tree']:
        raise RuntimeError('Public tree receipt mismatch')
    expected = receipt['expected_remote']
    if expected is not None:
        oid(expected)
    if candidate != expected and candidate != anchor:
        parents = run('show', '-s', '--format=%P', candidate).decode().split()
        if parents != [expected or anchor]:
            raise RuntimeError('Candidate parent differs from reviewed public remote snapshot')
    public_history(candidate, source, manifest)
    records = [{'path': path, 'mode': entry[0], 'blob': entry[2]} for path, entry in selected.items()]
    if receipt['files'] != records:
        raise RuntimeError('Per-file provenance differs from committed source')
    return selected

def prepare(message):
    source = clean_source()
    manifest, digest = load_manifest(source)
    selected = select(entries(source), manifest)
    anchor = manifest['public_anchor']
    remote = remote_head(manifest)
    parent = remote or anchor
    if remote is None and remote_head(manifest, manifest['anchor_ref']) != anchor:
        raise RuntimeError('Initial public anchor is not at the configured anchor ref')
    present = run('cat-file', '-t', parent, allowed=(0, 128)).strip()
    if present != b'commit':
        destination_guard(manifest)
        run('fetch', '--no-tags', '--no-auto-maintenance', manifest['public_url'],
            manifest['public_ref'] if remote else manifest['anchor_ref'], timeout=90)
    public_history(parent, source, manifest)
    tree = build_tree(selected)
    if run('rev-parse', parent + '^{tree}').decode().strip() == tree:
        candidate = parent
    else:
        if not message or len(message) > 120 or '\n' in message or '\r' in message:
            raise RuntimeError('Use a short reviewed public commit title')
        candidate = oid(run('commit-tree', tree, '-p', parent, '-m', message).decode().strip())
    receipt = {'schema': 1, 'private_sha': source, 'public_sha': candidate, 'public_ref': manifest['public_ref'], 'public_url': manifest['public_url'],
               'expected_remote': remote, 'tree': tree, 'manifest_sha256': digest,
               'files': [{'path': path, 'mode': item[0], 'blob': item[2]} for path, item in selected.items()]}
    validate_candidate(receipt, source)
    path = host_target('.local/export/' + source + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    return path, receipt

def publish(path):
    source = clean_source()
    receipt = json.loads(path.read_text(encoding='utf-8'))
    validate_candidate(receipt, source)
    manifest, _ = load_manifest(source)
    current = remote_head(manifest)
    candidate = receipt['public_sha']
    if current == candidate:
        return 'ALREADY_PUBLISHED', receipt
    if current != receipt['expected_remote']:
        raise RuntimeError('Public ref changed; prepare/review a fresh export')
    # Explicit SHA/ref only. The normal public remote stays DISABLED.
    destination_guard(manifest)
    run('push', manifest['public_url'], candidate + ':' + manifest['public_ref'], timeout=90)
    if remote_head(manifest) != candidate:
        raise RuntimeError('Public SHA verification failed; inspect before retrying')
    return 'PUBLISHED', receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--message', required=True)
    for name in ['verify', 'publish']:
        p = sub.add_parser(name); p.add_argument('receipt', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        path, receipt = prepare(args.message); state = 'PREPARED'
    elif args.action == 'publish':
        state, receipt = publish(args.receipt); path = args.receipt
    else:
        receipt = json.loads(args.receipt.read_text(encoding='utf-8'))
        validate_candidate(receipt, receipt['private_sha']); path = args.receipt; state = 'VERIFIED'
    print(json.dumps({'status': state, 'private_sha': receipt['private_sha'], 'public_sha': receipt['public_sha'],
                      'files': len(receipt['files']), 'receipt': str(path)}))
