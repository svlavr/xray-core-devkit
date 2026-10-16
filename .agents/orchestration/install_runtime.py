"""Install SHA-pinned Linux runtime assets in a deliberately selected fresh prefix.

This does not create a WSL distribution, city, user, authentication or repositories.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import tarfile
import tempfile
import urllib.request


def inspect_archive(archive, asset):
    """Validate archive paths before extraction; retain Codex's resource tree."""
    names = []
    for member in archive.getmembers():
        path = Path(member.name)
        if path.is_absolute() or '..' in path.parts or member.isdev() or member.isfifo():
            raise ValueError('Unsafe archive member: ' + member.name)
        names.append(member.name.removeprefix('./'))
    required = asset.get('required_members', [])
    if any(name not in names for name in required):
        raise ValueError('Pinned archive lacks required package resources: ' + asset['name'])


def install(lock_path, prefix, bindir):
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise RuntimeError('Runtime lock targets Linux amd64; run inside the selected Linux distribution')
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    if lock.get('platform') != 'linux-amd64':
        raise ValueError('Unsupported runtime lock platform')
    assets = lock['assets']
    # Never replace an existing runtime or partially overwrite another install.
    if prefix.exists():
        raise FileExistsError('Select a fresh prefix; existing runtime is preserved: ' + str(prefix))
    for asset in assets:
        target = bindir / asset['executable']
        if target.exists() or target.is_symlink():
            raise FileExistsError('Existing command is preserved: ' + str(target))
    with tempfile.TemporaryDirectory(prefix='xray-runtime-') as folder:
        staging = Path(folder)
        packages = []
        for asset in assets:
            path = staging / (asset['name'] + '.tar.gz')
            with urllib.request.urlopen(asset['url'], timeout=60) as source, path.open('wb') as output:
                shutil.copyfileobj(source, output)
            if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
                raise ValueError('Asset SHA256 mismatch: ' + asset['name'])
            package = staging / asset['name']
            package.mkdir()
            with tarfile.open(path) as archive:
                inspect_archive(archive, asset)
                archive.extractall(package, filter='data')
            required = asset.get('required_members')
            matches = ([package / 'bin' / asset['executable']] if required else
                       [p for p in package.rglob(asset['executable']) if p.is_file() and not p.is_symlink()])
            if len(matches) != 1 or not matches[0].is_file():
                raise ValueError('Ambiguous/missing executable: ' + asset['name'])
            packages.append((asset, package, matches[0].relative_to(package)))
        prefix.mkdir(parents=True, exist_ok=False)
        bindir.mkdir(parents=True, exist_ok=True)
        for asset, package, relative in packages:
            destination = prefix / asset['name']
            shutil.copytree(package, destination)
            executable = destination / relative
            executable.chmod(executable.stat().st_mode | 0o111)
            (bindir / asset['executable']).symlink_to(executable)
        (prefix / 'runtime-lock.json').write_bytes(lock_path.read_bytes())
    return {'prefix': str(prefix), 'commands': [str(bindir / a['executable']) for a in assets],
            'installed': True, 'model_run_qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--bin-dir', type=Path, default=Path('/usr/local/bin'))
    args = parser.parse_args()
    print(json.dumps(install(args.lock.resolve(), args.prefix.resolve(), args.bin_dir.absolute())))
