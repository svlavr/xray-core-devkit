"""Check the reviewed public distribution for host paths and credential patterns."""
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

import devkit


def audit(root=devkit.ROOT):
    manifest = devkit.verify(root)
    findings = []
    expressions = [
        ('personal-profile-path', re.compile(r'(?i)(?:[a-z]:[\\/]+Users[\\/]+(?!Public\b|<)[^\s"\'<>]+|/home/(?!<|worker/)[a-z0-9_-]+/)')),
        ('private-key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
        ('github-token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b')),
        ('credential-url', re.compile(r'https?://[^\s/@:]+:[^\s/@]+@[^\s/"\'<>]+')),
    ]
    for name in manifest['files']:
        data = (root / name).read_text(encoding='utf-8')
        if name.endswith('package-lock.json'):
            lock = json.loads(data)
            for package in lock.get('packages', {}).values():
                if str(package.get('resolved', '')).startswith(('file:', 'git+file:', '/', 'C:', 'D:', 'E:')):
                    findings.append({'file': name, 'kind': 'local-dependency-resolution'})
        for kind, pattern in expressions:
            for match in pattern.finditer(data):
                if kind == 'credential-url' and Path(name).name.startswith('test_'):
                    hostname = urlsplit(match.group()).hostname or ''
                    if hostname.endswith('.invalid'):
                        # Reserved-domain negative policy fixtures contain no
                        # usable account or endpoint; keep their regression.
                        continue
                # Do not print potential credentials, only their location.
                findings.append({'file': name, 'kind': kind,
                                 'line': data.count('\n', 0, match.start()) + 1})
    if findings:
        return {'status': 'REVIEW_REQUIRED', 'findings': findings}
    return {'status': 'PASS', 'files': len(manifest['files']),
            'boundary': 'Generic pattern check plus explicit manifest; human content review remains required'}


if __name__ == '__main__':
    try:
        result = audit()
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['status'] == 'PASS' else 1)
    except (OSError, ValueError) as error:
        print('AUDIT_REFUSED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
