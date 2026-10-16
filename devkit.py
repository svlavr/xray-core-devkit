"""Install, update and package this independent Xray Core DevKit snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
MANIFEST = 'devkit-manifest.json'
STATE = '.local/workspace/devkit-install.json'
BEGIN = '<!-- xray-core-devkit:begin -->'
END = '<!-- xray-core-devkit:end -->'
GUIDANCE = '''For Xray development, read `.agents/CODEX_PACK.md` and the relevant
`.agents/skills/*/SKILL.md`. Use `docs/PROJECT_SCOPE.md` to establish the human's
current task and evidence boundaries. Project-specific human instructions take
precedence over the toolkit defaults. No publication is authorized by installation.'''
IGNORES = '.local/\n.codex/config.toml\n.codex/hooks.json\n.codex-remote-attachments/\n**/__pycache__/\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def installed_sha(data):
    # The distribution is LF-pinned. A target checkout can legitimately expand
    # text to CRLF through its own Git settings; this is not a local code edit.
    return sha(data.replace(b'\r\n', b'\n'))


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('Expected a relative POSIX path')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('', '.', '..') or x.endswith((' ', '.')) for x in value.split('/')):
        raise ValueError('Unsafe distribution path: ' + value)
    if any(ord(c) < 32 for c in value):
        raise ValueError('Control character in distribution path')
    return p.as_posix()


def plain(root, value):
    """Do not follow user symlinks, reparse points or aliased files."""
    path = root / relative(value)
    for item in [root, *[root.joinpath(*path.relative_to(root).parts[:i])
                         for i in range(1, len(path.relative_to(root).parts) + 1)]]:
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Refusing linked or reparse path: ' + str(item))
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ValueError('Refusing aliased file: ' + str(item))
    if not path.resolve().is_relative_to(root):
        raise ValueError('Path escapes selected root')
    return path


def public_files(root=ROOT):
    """Deliberate public allowlist; host state and Git ancestry never enter it."""
    files = []
    for folder in ('.agents', '.codex/agents', 'docs', 'examples', 'dependencies', 'tests'):
        base = root / folder
        if base.is_dir():
            for path in sorted(base.rglob('*')):
                rel = path.relative_to(root).as_posix()
                if '__pycache__' in path.parts or path.suffix == '.pyc':
                    continue
                if path.is_file():
                    plain(root, rel)
                    if any(part in {'.local', '.private', '.git', 'node_modules', '.codex-remote-attachments'}
                           for part in path.relative_to(root).parts):
                        raise ValueError('Host/private data inside public payload: ' + rel)
                    if path.name.lower() in {'auth.json', 'credentials.json', '.env'} or path.name.startswith('.env.'):
                        raise ValueError('Credential filename inside public payload: ' + rel)
                    if rel in {'.agents/project.json', '.agents/public-export.json',
                               '.agents/metrics/modules.json', '.agents/metrics/source-size.json',
                               '.agents/metrics/shared-integration.json'}:
                        raise ValueError('Project-specific input inside public payload: ' + rel)
                    files.append(rel)
    for name in ('devkit.py', 'audit.py', 'README.md', 'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md',
                 'AGENTS.md', '.gitignore', '.gitattributes'):
        if (root / name).is_file():
            plain(root, name)
            files.append(name)
    return sorted(set(files))


def build_manifest(root=ROOT):
    return {'schema': 1, 'name': 'xray-core-devkit',
            'files': {p: sha((root / p).read_bytes()) for p in public_files(root)}}


def read_manifest(root=ROOT):
    value = json.loads((root / MANIFEST).read_text(encoding='utf-8'))
    if value.get('schema') != 1 or value.get('name') != 'xray-core-devkit' or not value.get('files'):
        raise ValueError('Unsupported or empty devkit manifest')
    seen = set()
    for name, digest in value['files'].items():
        relative(name)
        if name.casefold() in seen or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Invalid or aliased manifest entry')
        seen.add(name.casefold())
    return value


def verify(root=ROOT):
    expected = read_manifest(root)
    actual = build_manifest(root)
    if expected != actual:
        changed = sorted(p for p in expected['files'].keys() | actual['files'].keys()
                         if expected['files'].get(p) != actual['files'].get(p))
        raise ValueError('Public manifest mismatch: ' + ', '.join(changed))
    return expected


def payload(manifest):
    return {p: h for p, h in manifest['files'].items()
            if p.startswith(('.agents/', '.codex/agents/', 'docs/', 'examples/'))}


def block(text, content, previous=None):
    """Preserve unrelated instructions; refuse editing a modified managed block."""
    desired = BEGIN + '\n' + content.rstrip() + '\n' + END
    if BEGIN not in text and END not in text:
        return text.rstrip() + ('\n\n' if text.strip() else '') + desired + '\n'
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('Ambiguous devkit managed block')
    start, end = text.index(BEGIN), text.index(END) + len(END)
    current = text[start:end]
    if end < start or (current != desired and previous is not None and sha(current.encode()) != previous):
        raise ValueError('Managed instructions were edited; reconcile them before updating')
    if previous is None and current != desired:
        raise ValueError('Existing devkit instructions need explicit reconciliation')
    return text[:start] + desired + text[end:]


def atomic_write(path, data):
    """Keep old bytes intact if a write is interrupted before replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.devkit-', suffix='.tmp', dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def install(target, *, update=False, dry_run=False, root=ROOT):
    selected = target.absolute()
    if selected != selected.resolve():
        raise ValueError('Target must be a direct canonical path')
    target = selected.resolve()
    if target == root.resolve() or not (target / 'go.mod').is_file():
        raise ValueError('Select a separate Xray source checkout containing go.mod')
    if not re.search(r'^module\s+github\.com/xtls/xray-core\s*$',
                     (target / 'go.mod').read_text(encoding='utf-8'), re.M):
        raise ValueError('Target is not an Xray Go module')
    manifest = verify(root)
    desired = {name: installed_sha((root / name).read_bytes()) for name in payload(manifest)}
    state_path = plain(target, STATE)
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else None
    if update != (state is not None):
        raise ValueError('Use update for an installed target, install for a new target')
    if state and (state.get('schema') != 1 or state.get('target') != str(target)):
        raise ValueError('Installed state belongs to another target or schema')
    prior = state['files'] if state else {}
    # A removed file needs a reviewed explicit retirement, never recursive cleanup.
    retired = sorted(set(prior) - set(desired))
    if retired:
        raise ValueError('Retired managed files require explicit review: ' + ', '.join(retired))
    writes, conflicts = {}, []
    for name, expected in desired.items():
        destination = plain(target, name)
        if destination.exists() and not destination.is_file():
            raise ValueError('Managed destination is not a regular file: ' + name)
        existing = destination.read_bytes() if destination.is_file() else None
        current = installed_sha(existing) if existing is not None else None
        previous_raw_matches = existing is not None and sha(existing) == prior.get(name)
        if current is not None and current not in (expected, prior.get(name)) and not previous_raw_matches:
            conflicts.append(name)
        elif current != expected:
            writes[name] = (root / name).read_bytes()
    managed = {}
    for name, content in [('AGENTS.md', GUIDANCE), ('.gitignore', IGNORES)]:
        destination = plain(target, name)
        if destination.exists() and not destination.is_file():
            raise ValueError('Managed instructions are not regular files: ' + name)
        text = destination.read_text(encoding='utf-8') if destination.exists() else ''
        replacement = block(text, content, (state or {}).get('blocks', {}).get(name))
        if replacement != text:
            writes[name] = replacement.encode('utf-8')
        managed[name] = sha((BEGIN + '\n' + content.rstrip() + '\n' + END).encode())
    if conflicts:
        raise ValueError('Preserved locally modified/conflicting files: ' + ', '.join(conflicts))
    report = {'status': 'PLANNED' if dry_run else 'INSTALLED', 'target': str(target),
              'files': len(desired), 'writes': sorted(writes), 'source': 'independent snapshot',
              'publication_authorized': False}
    if dry_run:
        return report
    # All conflicts/aliases are checked before the first write. The state is last;
    # interrupted installs are recoverable because identical bytes are accepted.
    for name, data in writes.items():
        path = plain(target, name)
        atomic_write(path, data)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(state_path, (json.dumps({'schema': 1, 'target': str(target), 'files': desired,
                                        'blocks': managed}, indent=2) + '\n').encode('utf-8'))
    return report


def archive(output, root=ROOT):
    manifest = verify(root)
    output = output.absolute()
    if output.exists():
        raise ValueError('Archive already exists; select a new output path')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as handle:
        for name in [*manifest['files'], MANIFEST]:
            handle.writestr('xray-core-devkit/' + name, (root / name).read_bytes())
    return {'status': 'PACKAGED', 'output': str(output),
            'files': len(manifest['files']) + 1, 'sha256': sha(output.read_bytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('manifest', help='Regenerate hashes after reviewing public files')
    sub.add_parser('verify', help='Verify the complete public distribution')
    for name in ('install', 'update'):
        command = sub.add_parser(name)
        command.add_argument('--target', type=Path, required=True)
        command.add_argument('--dry-run', action='store_true')
    package = sub.add_parser('package')
    package.add_argument('--output', type=Path, default=ROOT / '.local/dist/xray-core-devkit.zip')
    args = parser.parse_args()
    if args.action == 'manifest':
        value = build_manifest()
        atomic_write(ROOT / MANIFEST, (json.dumps(value, indent=2) + '\n').encode('utf-8'))
        result = {'status': 'MANIFEST_WRITTEN', 'files': len(value['files'])}
    elif args.action == 'verify':
        result = {'status': 'VERIFIED', 'files': len(verify()['files'])}
    elif args.action == 'package':
        result = archive(args.output)
    else:
        result = install(args.target, update=args.action == 'update', dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print('DEVKIT_REFUSED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
