"""Offline per-file/module source size from Git blobs, including staged content."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CATALOG = '.agents/metrics/modules.json'
SNAPSHOT = '.agents/metrics/source-size.json'
CATEGORIES = ('runtime', 'tests', 'generated', 'test_support', 'docs', 'tooling', 'other')
METHOD = 'git-physical-lines-text-myers-no-renames-v1'
DIFF = ('diff', '--no-ext-diff', '--no-textconv', '--no-renames',
        '--text', '--diff-algorithm=myers', '--ita-invisible-in-index')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode()).hexdigest()


class Repo:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.attributes_source = None
        self.attributes_source = self.git('hash-object', '-t', 'tree', '--stdin', data=b'').decode().strip()

    def git(self, *args, data=None):
        command = ['git', '--no-pager', '-c', 'core.fsmonitor=false', '-c', 'gc.auto=0',
                   '-c', 'maintenance.auto=false', '-c', 'core.attributesFile=' + os.devnull,
                   '-C', str(self.root), *args]
        env = os.environ.copy()
        env['GIT_ATTR_NOSYSTEM'] = '1'
        if self.attributes_source:
            env['GIT_ATTR_SOURCE'] = self.attributes_source
        result = subprocess.run(command, input=data, capture_output=True, timeout=60,
                                env=env,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise ValueError(result.stderr.decode(errors='replace').strip() or 'Git command failed')
        return result.stdout

    def commit(self, ref):
        return self.git('rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode().strip()

    def tree(self, source):
        staged = source == 'INDEX'
        if staged:
            if any(e and e.split(b'\t', 1)[0].split()[-1] != b'0'
                   for e in self.git('ls-files', '--stage', '-z').split(b'\0')):
                raise ValueError('Unmerged index entries cannot be measured')
            head = self.commit('HEAD')
            files = self.tree(head)
            # Reconstruct the staged view, omitting intent-to-add entries without
            # confusing them with genuinely staged empty files. No write-tree.
            raw = self.git(*DIFF, '--cached', '--raw', '--no-abbrev', '-z', head, '--').split(b'\0')
            for i in range(0, len(raw) - 1, 2):
                meta, path = raw[i], raw[i + 1].decode('utf-8')
                old_mode, new_mode, old_oid, new_oid, status = meta.decode().split()
                if new_mode == '000000':
                    files.pop(path, None)
                else:
                    files[path] = (new_mode, new_oid)
            return files
        raw = self.git('ls-tree', '-r', '-z', source)
        files = {}
        for entry in raw.split(b'\0'):
            if not entry:
                continue
            meta, path = entry.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            if kind != 'blob':
                raise ValueError('Submodules need an explicit inventory disposition')
            files[path.decode('utf-8')] = (mode, oid)
        return files

    def blobs(self, oids):
        wanted = sorted(set(oids))
        if not wanted:
            return {}
        data = self.git('cat-file', '--batch', data=('\n'.join(wanted) + '\n').encode())
        result, offset = {}, 0
        for wanted_oid in wanted:
            end = data.index(b'\n', offset)
            oid, kind, size = data[offset:end].split()
            if oid.decode() != wanted_oid or kind != b'blob':
                raise ValueError('Expected immutable Git blob: ' + wanted_oid)
            start, size = end + 1, int(size)
            result[wanted_oid] = data[start:start + size]
            offset = start + size + 1
        return result

    def text(self, source, path):
        return self.text_from_tree(self.tree(source), path)

    def text_from_tree(self, files, path):
        if path not in files:
            raise ValueError('Missing tracked ' + path)
        return self.blobs([files[path][1]])[files[path][1]]


def category(path):
    if path.startswith('.private/fixtures/'):
        return 'test_support'
    if path.startswith(('.agents/', '.codex/', '.github/')) or path.startswith('AGENTS'):
        return 'tooling'
    if path.startswith('.private/'):
        return 'docs' if path.endswith('.md') else 'tooling'
    if path.endswith('_test.go'):
        return 'tests'
    if path.endswith('.pb.go'):
        return 'generated'
    if path.startswith('testing/'):
        return 'test_support'
    if path.endswith('.go'):
        return 'runtime'
    if path.endswith(('.md', '.rst', '.txt')):
        return 'docs'
    return 'other'


def catalog_read(repo, source, override=None):
    data = Path(override).read_bytes() if override else repo.text(source, CATALOG)
    return catalog_parse(data)


def catalog_parse(data):
    catalog = json.loads(data)
    if (catalog.get('schema') != 1 or not isinstance(catalog.get('modules'), dict)
            or not catalog['modules'] or 'shared' in catalog['modules']
            or any(not isinstance(name, str) or not name for name in catalog['modules'])):
        raise ValueError('Unsupported owner catalog; supply named modules (shared is reserved)')
    if not isinstance(catalog.get('shared_fork_paths'), list):
        raise ValueError('Explicit shared_fork_paths list required')
    for group in [*catalog['modules'].values(), {'paths': catalog['shared_fork_paths']}]:
        if not isinstance(group, dict):
            raise ValueError('Owner rules must be objects')
        if any(not isinstance(group.get(key, []), list) for key in ('paths', 'prefixes')):
            raise ValueError('Owner paths/prefixes must be lists')
        for path in group.get('paths', []) + group.get('prefixes', []):
            if not isinstance(path, str) or not path or ':' in path or path.startswith('/') or '\\' in path or '..' in path.split('/'):
                raise ValueError('Invalid owner path: ' + path)
    return catalog


def owner(path, catalog, upstream_files):
    matches = [name for name, rules in catalog['modules'].items()
               if path in rules.get('paths', []) or
               any(path.startswith(prefix) for prefix in rules.get('prefixes', []))]
    if len(matches) > 1:
        raise ValueError('Ambiguous module owner: ' + path)
    if matches:
        return matches[0]
    if category(path) == 'runtime' and path not in upstream_files and path not in catalog['shared_fork_paths']:
        raise ValueError('Unmapped fork runtime file: ' + path)
    return 'shared'


def included(path):
    return not path.startswith(('.agents/metrics/', '.local/', '.codex-remote-attachments/')) and path != '.codex/config.toml'


def line_count(data):
    if b'\0' in data[:8000]:
        return None
    return data.count(b'\n') + int(bool(data) and not data.endswith(b'\n'))


def build(repo, source, upstream, catalog):
    upstream = repo.commit(upstream)
    head = repo.commit('HEAD') if source == 'INDEX' else None
    current, native = repo.tree(source), repo.tree(upstream)
    selected = {p for p in set(current) | set(native) if included(p)}
    blobs = repo.blobs([entry[1] for tree in (current, native) for p, entry in tree.items() if p in selected])
    args = [*DIFF, '--numstat', '-z']
    raw = repo.git(*args, '--cached', upstream) if source == 'INDEX' else repo.git(*args, upstream, source)
    changes = {}
    for entry in raw.split(b'\0'):
        if entry:
            added, deleted, path = entry.split(b'\t', 2)
            changes[path.decode('utf-8')] = (None, None) if added == b'-' else (int(added), int(deleted))
    files = []
    for path in sorted(selected):
        now, original = current.get(path), native.get(path)
        cat = category(path)
        if now and now[0] not in ('100644', '100755') and cat == 'runtime':
            raise ValueError('Runtime source must be a regular Git file: ' + path)
        added, deleted = changes.get(path, (0, 0))
        total = line_count(blobs[now[1]]) if now else 0
        before = line_count(blobs[original[1]]) if original else 0
        if (total is None or before is None) and path in changes:
            added, deleted = None, None
        if cat == 'runtime' and (added is None or total is None or before is None):
            raise ValueError('Binary runtime source cannot be counted: ' + path)
        files.append({'path': path, 'module': owner(path, catalog, native), 'category': cat,
                      'present': now is not None, 'mode': now[0] if now else None,
                      'blob': now[1] if now else None, 'lines': total, 'upstream_lines': before,
                      'fork_changed': path in changes, 'added': added, 'deleted': deleted,
                      'net': added - deleted if added is not None else None})
    modules = (*catalog['modules'], 'shared')
    summaries = {}
    for module in modules:
        summaries[module] = {}
        for cat in CATEGORIES:
            rows = [r for r in files if r['module'] == module and r['category'] == cat]
            summaries[module][cat] = {'files': sum(r['present'] for r in rows),
                'lines': sum(r['lines'] or 0 for r in rows),
                'binary_files': sum(r['present'] and r['lines'] is None for r in rows),
                'unknown_fork_files': sum(r['fork_changed'] and r['net'] is None for r in rows),
                'partial': any((r['present'] and r['lines'] is None) or
                               (r['fork_changed'] and r['net'] is None) for r in rows),
                'fork_changed_files': sum(r['fork_changed'] for r in rows),
                'added': sum(r['added'] or 0 for r in rows), 'deleted': sum(r['deleted'] or 0 for r in rows),
                'net': sum(r['net'] or 0 for r in rows)}
    fingerprint = digest([(p, *current[p]) for p in sorted(current) if included(p)])
    runtime_fingerprint = digest([(p, *current[p]) for p in sorted(current) if category(p) == 'runtime' and included(p)])
    totals = {cat: {key: (any(summaries[m][cat][key] for m in modules) if key == 'partial'
                         else sum(summaries[m][cat][key] for m in modules))
                    for key in summaries['shared'][cat]} for cat in CATEGORIES}
    if repo.tree(source) != current or (head and repo.commit('HEAD') != head):
        raise ValueError('Source/index changed during measurement; retry after writer finishes')
    return {'schema': 1, 'method': METHOD, 'upstream_sha': upstream,
            'catalog_sha256': digest(catalog), 'source_fingerprint': fingerprint,
            'runtime_fingerprint': runtime_fingerprint, 'modules': summaries, 'totals': totals, 'files': files}


def verify(repo, source='HEAD', catalog_override=None, snapshot_override=None):
    source = source if source == 'INDEX' else repo.commit(source)
    head = repo.commit('HEAD') if source == 'INDEX' else None
    view = repo.tree(source)
    snapshot_data = (Path(snapshot_override).read_bytes() if snapshot_override else
                     repo.text_from_tree(view, SNAPSHOT))
    catalog_data = (Path(catalog_override).read_bytes() if catalog_override else
                    repo.text_from_tree(view, CATALOG))
    recorded = json.loads(snapshot_data)
    expected = build(repo, source, recorded['upstream_sha'], catalog_parse(catalog_data))
    if (repo.tree(source) != view or (head and repo.commit('HEAD') != head) or
            (snapshot_override and Path(snapshot_override).read_bytes() != snapshot_data) or
            (catalog_override and Path(catalog_override).read_bytes() != catalog_data)):
        raise ValueError('Source/index or metadata changed during verification; retry after writer finishes')
    if recorded != expected:
        raise ValueError('Source-size snapshot is stale or inconsistent; regenerate from exact source/index')
    return recorded


def report(before, after):
    changed = []
    previous = {r['path']: r for r in before['files']}
    for row in after['files']:
        old = previous.pop(row['path'], None)
        if old != row:
            changed.append({'path': row['path'], 'module': row['module'], 'category': row['category'],
                            'before_lines': old['lines'] if old else 0, 'after_lines': row['lines'],
                            'before_fork_net': old['net'] if old else 0, 'after_fork_net': row['net']})
    changed += [{'path': r['path'], 'module': r['module'], 'category': r['category'],
                 'before_lines': r['lines'], 'after_lines': 0,
                 'before_fork_net': r['net'], 'after_fork_net': 0} for r in previous.values()]
    modules = sorted(set(before['modules']) | set(after['modules']))
    def summary(snapshot, module, cat, key):
        return snapshot['modules'].get(module, {}).get(cat, {}).get(key, 0)
    deltas = {module: {cat: {key: summary(after, module, cat, key) - summary(before, module, cat, key)
                            for key in ('files', 'lines', 'fork_changed_files', 'added', 'deleted', 'net')}
                      for cat in CATEGORIES} for module in modules}
    return {'upstream_before': before['upstream_sha'], 'upstream_after': after['upstream_sha'],
            'baseline_changed': before['upstream_sha'] != after['upstream_sha'],
            'catalog_changed': before['catalog_sha256'] != after['catalog_sha256'],
            'runtime_unchanged': before['runtime_fingerprint'] == after['runtime_fingerprint'],
            'before': before['modules'], 'after': after['modules'], 'delta': deltas,
            'runtime_growth_owners': [m for m in modules if deltas[m]['runtime']['net'] > 0],
            'changed_files': changed}


def startup_check(repo=None):
    repo = repo or Repo()
    head = repo.commit('HEAD')
    files = repo.tree(head)
    if CATALOG not in files and SNAPSHOT not in files:
        return {'status': 'UNINITIALIZED', 'required': [CATALOG, SNAPSHOT]}
    snap = verify(repo, head)
    index = repo.tree('INDEX')
    dirty = digest([(p, *index[p]) for p in sorted(index) if included(p)]) != snap['source_fingerprint']
    # Worktree changes are reported separately; only immutable HEAD is verified here.
    unstaged = bool(repo.git('diff', '--name-only'))
    if repo.commit('HEAD') != head:
        raise ValueError('HEAD moved during source-size startup check')
    untracked = [p.decode('utf-8') for p in repo.git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if p]
    return {'status': 'VERIFIED_HEAD', 'commit': head, 'source_fingerprint': snap['source_fingerprint'],
            'upstream_sha': snap['upstream_sha'], 'pending_index_changes': dirty,
            'pending_worktree_changes': unstaged, 'untracked_candidates': untracked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['snapshot', 'verify', 'report', 'history'])
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--source', default='HEAD')
    parser.add_argument('--upstream')
    parser.add_argument('--catalog', type=Path)
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--before', type=Path)
    parser.add_argument('--after', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    repo = Repo(args.repo)
    if args.action == 'snapshot':
        if not args.upstream:
            parser.error('snapshot requires --upstream <exact adopted official ref>')
        source = args.source if args.source == 'INDEX' else repo.commit(args.source)
        result = build(repo, source, args.upstream, catalog_read(repo, source, args.catalog))
    elif args.action == 'verify':
        snap = verify(repo, args.source, args.catalog, args.snapshot)
        result = {'status': 'VERIFIED', 'source': args.source, 'upstream_sha': snap['upstream_sha'],
                  'source_fingerprint': snap['source_fingerprint'], 'modules': snap['modules']}
    elif args.action == 'report':
        if not args.before or not args.after:
            parser.error('report requires --before and --after snapshots')
        result = report(json.loads(args.before.read_bytes()), json.loads(args.after.read_bytes()))
    else:
        if args.limit < 1:
            parser.error('history limit must be positive')
        result = []
        commits = repo.git('rev-list', '--first-parent', '--max-count=' + str(args.limit), 'HEAD').decode().splitlines()
        for commit in commits:
            if SNAPSHOT not in repo.tree(commit):
                result.append({'commit': commit, 'status': 'LEGACY_NOT_RECORDED'})
                continue
            snap = verify(repo, commit)
            result.append({'commit': commit, 'status': 'VERIFIED', 'upstream_sha': snap['upstream_sha'],
                           'runtime_fingerprint': snap['runtime_fingerprint'], 'modules': snap['modules']})
    text = json.dumps(result, indent=2, ensure_ascii=True) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8', newline='\n')
        print(json.dumps({'output': str(args.output), 'status': 'WRITTEN'}))
    else:
        print(text, end='')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('SOURCE_SIZE_BLOCKED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
