"""Provision the recorded analysis dependency set into an explicit local tools root."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

from resource_guard import run, plain_path

ROOT = Path(__file__).resolve().parents[2]
LOCKS = Path(__file__).resolve().parents[1] / 'dependencies'
FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def metadata():
    value = json.loads((LOCKS / 'analysis-lock.json').read_text(encoding='utf-8'))
    if value.get('schema') != 1:
        raise ValueError('Unsupported dependency lock')
    return value


def safe_file(path):
    path = plain_path(path)
    if path.exists():
        information = path.lstat()
        if not stat.S_ISREG(information.st_mode) or information.st_nlink != 1:
            raise ValueError('Dependency file must be regular and unaliased: ' + str(path))
    return path


def npm_command(node):
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    candidates = [Path(node).parent / 'node_modules/npm/bin/npm-cli.js']
    if npm:
        candidates.extend([Path(npm).parent / 'node_modules/npm/bin/npm-cli.js',
                           Path(npm).resolve().parent.parent / 'lib/node_modules/npm/bin/npm-cli.js'])
        if os.name != 'nt':
            candidates.append(Path(npm).resolve())
    for candidate in candidates:
        if candidate.is_file():
            return [str(node), str(candidate)]
    raise RuntimeError('npm-cli.js is unavailable; install Node with npm')


def installed(tools):
    locks = metadata()
    result = {'tools': str(tools), 'go_tools': {}, 'npm': {}, 'configured_only': True}
    for name in locks['go_tools']:
        binary = tools / 'bin' / (name + ('.exe' if os.name == 'nt' else ''))
        result['go_tools'][name] = {'exists': binary.is_file(), 'path': str(binary)}
    for name, specification in locks['npm'].items():
        package = tools / name / 'node_modules' / specification['package'] / 'package.json'
        actual = json.loads(package.read_text(encoding='utf-8')) if package.is_file() else {}
        result['npm'][name] = {'expected': specification['version'], 'actual': actual.get('version'),
                               'matches': actual.get('version') == specification['version']}
    return result


def provision(tools):
    locks = metadata()
    tools = tools.absolute()
    plain_path(tools)
    if tools != tools.resolve():
        raise ValueError('Tools root must be a direct canonical path')
    go = shutil.which('go')
    node = shutil.which('node')
    if not go or not node:
        raise RuntimeError('Install Go and Node first; see docs/INSTALLATION.md')
    npm = npm_command(node)
    plain_path(tools / 'bin')
    for name in ('gopls', 'deadcode', 'ast-grep'):
        safe_file(tools / 'bin' / (name + ('.exe' if os.name == 'nt' else '')))
    # Do not mix an unrelated tools layout with an installation silently.
    for name in locks['npm']:
        destination = tools / name
        plain_path(destination)
        plain_path(destination / 'node_modules')
        if destination.is_symlink() or (destination.exists() and destination.resolve() != destination):
            raise ValueError('Dependency path must not be a link: ' + str(destination))
        for filename in ('package.json', 'package-lock.json'):
            target = destination / filename
            safe_file(target)
            if target.exists() and target.read_bytes() != (LOCKS / name / filename).read_bytes():
                raise ValueError('Existing dependency metadata differs: ' + str(target))
    tools.mkdir(parents=True, exist_ok=True)
    (tools / 'bin').mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(GOBIN=str(tools / 'bin'), GOWORK='off')
    # The pinned gopls build requires the recorded Go toolchain capability.
    for specification in locks['go_tools'].values():
        run([go, 'install', specification], env=env, cwd=ROOT, timeout=600, check=True,
            stdin=subprocess.DEVNULL, creationflags=FLAGS)
    for name in locks['npm']:
        destination = tools / name
        destination.mkdir(exist_ok=True)
        for filename in ('package.json', 'package-lock.json'):
            shutil.copyfile(LOCKS / name / filename, destination / filename)
        run([*npm, 'ci', '--no-audit', '--no-fund'], cwd=destination, timeout=900, check=True,
            stdin=subprocess.DEVNULL, creationflags=FLAGS)
    # The CLI binary is supplied by ast-grep's pinned npm package, not copied
    # from a developer machine or a package-manager global directory.
    package = tools / 'ast-grep/node_modules/@ast-grep/cli'
    executable = package / ('ast-grep.exe' if os.name == 'nt' else 'ast-grep')
    if not executable.is_file():
        raise RuntimeError('Pinned ast-grep package did not provide its binary')
    shutil.copyfile(executable, tools / 'bin' / executable.name)
    if os.name != 'nt':
        (tools / 'bin' / executable.name).chmod(0o755)
    return installed(tools)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'status'])
    parser.add_argument('--tools', type=Path, required=True)
    args = parser.parse_args()
    result = provision(args.tools) if args.action == 'install' else installed(args.tools.resolve())
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('DEPENDENCIES_REFUSED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
