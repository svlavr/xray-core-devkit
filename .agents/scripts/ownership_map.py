"""Verify a user-reviewed shared-runtime ownership map against exact Git blobs."""
import argparse
import json
import sys

import source_size


def validate(repo, source):
    head = repo.commit('HEAD')
    selected = 'INDEX' if source == 'INDEX' else head
    view = repo.tree(selected)
    snapshot = source_size.verify(repo, selected)
    catalog = source_size.catalog_parse(repo.text_from_tree(view, source_size.CATALOG))
    path = catalog.get('semantic_map', '.agents/metrics/shared-integration.json')
    if (not isinstance(path, str) or not path or path.startswith('/') or ':' in path
            or '\\' in path or '..' in path.split('/')):
        raise ValueError('Invalid semantic map path')
    modules = {*catalog['modules'], 'native'}
    semantic = json.loads(repo.text_from_tree(view, path))
    if semantic['upstream_sha'] != snapshot['upstream_sha']:
        raise ValueError('Ownership map upstream differs from adopted clean baseline')
    if semantic['runtime_fingerprint'] != snapshot['runtime_fingerprint']:
        raise ValueError('Runtime changed: renew ownership/necessity evidence before checkpoint')
    expected = {f['path']: f for f in snapshot['files']
                if f['module'] == 'shared' and f['category'] == 'runtime' and f['fork_changed']}
    actual = {f['path']: f for f in semantic['files']}
    if len(actual) != len(semantic['files']) or set(actual) != set(expected):
        raise ValueError('Missing, duplicate or stale shared-runtime ownership path')
    for name, record in actual.items():
        for key in ('blob', 'lines', 'upstream_lines', 'added', 'deleted', 'net'):
            if record[key] != expected[name][key]:
                raise ValueError('Stale ownership file fact: ' + name + '/' + key)
        if not record['consumers'] or not record['blocks'] or not record['necessity'] or not record['removal_hazard']:
            raise ValueError('Incomplete necessity/removal evidence: ' + name)
        if record['primary_module'] not in modules:
            raise ValueError('Unknown semantic module: ' + name)
        if not record['module_relations'] or any(m not in modules for m in record['module_relations']):
            raise ValueError('Unknown/missing semantic consumers: ' + name)
    if repo.commit('HEAD') != head or repo.tree(selected) != view:
        raise ValueError('Source/index changed during ownership validation; retry after writer finishes')
    return {'status': 'VERIFIED', 'source': source, 'head': head, 'upstream_sha': snapshot['upstream_sha'],
            'shared_changed_files': len(actual), 'shared_net': sum(f['net'] for f in actual.values()),
            'runtime_fingerprint': snapshot['runtime_fingerprint']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=('HEAD', 'INDEX'), default='HEAD')
    args = parser.parse_args()
    try:
        print(json.dumps(validate(source_size.Repo(), args.source), indent=2))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'FAILED', 'error': str(exc)}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
