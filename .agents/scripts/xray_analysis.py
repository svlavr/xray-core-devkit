"""Checkout-scoped, on-demand access to the configured Xray analysis tools."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import uuid
import time
import zipfile
from resource_guard import run as guarded_run, check_cancelled, wait_custody

from local_environment import ROOT, host, git
TOOLS = Path(host()["analysis_tools"])
SCRIPTS = Path(__file__).resolve().parent
SOURCE_PATHS = ("app", "common", "core", "features", "infra", "main", "measurement", "proxy", "testing", "transport", "go.mod", "go.sum")
WORKSPACE_PATHS = ("go.work", "go.work.sum")
PROFILES = {"windows": ("windows", "amd64"), "android": ("android", "arm64"), "linux": ("linux", "amd64")}

GRAPH_SCHEMA = 2
GRAPH_PREPARE_SECONDS = 900
GRAPH_PREPARE_MAX_SECONDS = 1200
GRAPH_FLAGS = ("--skip-git", "--index-only", "--force", "--workers", "1")
GRAPH_EXCLUSIONS = (".local", ".agents", ".codex", "untracked files")
_analyzer_cache = None
_analyzer_lock = threading.Lock()


def graph_identity(deadline=None, cancelled=None) -> dict:
    """Bind an index to the installed analyzer bytes and our export contract."""
    global _analyzer_cache
    install = TOOLS / 'gitnexus'
    modules = install / 'node_modules'
    package = modules / 'gitnexus'
    if not (package / 'dist/cli/index.js').is_file():
        raise RuntimeError("GitNexus analyzer is unavailable")
    roots = [package / 'dist', *modules.glob('tree-sitter*'), *modules.glob('@ladybugdb/*')]
    files = [package / 'package.json', *install.glob('*lock*')]
    for root in roots:
        files.extend(path for path in root.rglob('*') if path.is_file() and
                     (path.suffix in ('.js', '.node', '.wasm', '.dll', '.so', '.dylib') or path.name == 'package.json'))
    files = sorted(set(path for path in files if path.is_file()))
    signature = []
    for path in files:
        if deadline is not None:remaining(deadline, 'analyzer identity', cancelled=cancelled)
        stat = path.stat()
        signature.append((str(path), stat.st_size, stat.st_mtime_ns))
    # Normal updates change file membership/size/mtime. This is freshness
    # identity, not a tamper-proof attestation of every transitive dependency.
    signature = tuple(signature)
    with _analyzer_lock:
        if _analyzer_cache is None or _analyzer_cache[0] != signature:
            digest = hashlib.sha256()
            for path in files:
                if deadline is not None:remaining(deadline, 'analyzer identity hash', cancelled=cancelled)
                digest.update(path.relative_to(install).as_posix().encode()+b'\0'+path.read_bytes())
            _analyzer_cache = (signature, digest.hexdigest())
        analyzer = {'version': json.loads((package / 'package.json').read_text(encoding='utf-8'))['version'],
                    'artifacts': _analyzer_cache[1],
                    'scope': 'build JS, lockfile, installed tree-sitter and Ladybug runtime artifacts',
                    'node': node_executable()}
    export = {"paths": SOURCE_PATHS, "excluded": GRAPH_EXCLUSIONS, "flags": GRAPH_FLAGS}
    return {"schema": GRAPH_SCHEMA, "analyzer": analyzer,
            "export": hashlib.sha256(json.dumps(export, sort_keys=True).encode()).hexdigest()}


def graph_progress() -> dict:
    try:
        value = json.loads((cache_root() / "graph-progress.json").read_text(encoding="utf-8"))
        if value.get("state") == "PREPARING":
            value["elapsed_seconds"] = round(max(0, time.time() - value["started_at"]), 3)
        return value
    except (OSError, ValueError, KeyError):
        return {}


def graph_key(status) -> dict:
    return {"fingerprint": status["source"]["fingerprint"], "identity": status["identity"]}


def graph_storage_valid(manifest, cache) -> bool:
    try:
        index = Path(manifest['index']).resolve()
        registry = Path(manifest['registry_home']).resolve()
        if not (index.is_relative_to(cache) and registry.is_relative_to(cache) and index.is_dir() and (index / 'lbug').exists()):
            return False
        meta = json.loads((index / 'meta.json').read_text(encoding='utf-8'))
        entries = json.loads((registry / 'registry.json').read_text(encoding='utf-8'))
        return (isinstance(meta, dict) and Path(meta['storagePath']).resolve() == index
                and Path(meta['repoPath']).resolve() == Path(manifest['snapshot']).resolve()
                and isinstance(entries, list) and any(isinstance(entry, dict)
                    and Path(entry.get('storagePath', '')).resolve() == index
                    and Path(entry.get('path', '')).resolve() == Path(manifest['snapshot']).resolve()
                    for entry in entries))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _build_graph(before, identity, base, deadline, cancelled, report):
    options = {'cancelled': cancelled} if cancelled is not None else {}
    # A unique output preserves earlier evidence and avoids partial-index reuse.
    run = Path(tempfile.mkdtemp(prefix="graph-", dir=base))
    report('source_archive', log=str(run / 'analyze.log'))
    snapshot = run / "source"
    snapshot.mkdir()
    archive = run / "source.zip"
    guarded_run([host()["git_executable"], "archive", "--format=zip", "--output=" + str(archive), before["head"], *committed_source_paths(before["head"], deadline=deadline, cancelled=cancelled)], cwd=ROOT, stdin=subprocess.DEVNULL, check=True, timeout=remaining(deadline,'source archive',20,cancelled=cancelled), cancelled=cancelled, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    with zipfile.ZipFile(archive) as handle:
        for entry in handle.infolist():
            remaining(deadline,'archive validation',cancelled=cancelled)
            target = (snapshot / entry.filename).resolve()
            if not target.is_relative_to(snapshot.resolve()) or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError("Unsafe archive member")
        for entry in handle.infolist():
            remaining(deadline,'archive extraction',cancelled=cancelled)
            handle.extract(entry,snapshot)
    home, index = run / "registry", run / "index"
    env = os.environ.copy()
    env.update(GITNEXUS_HOME=str(home), GITNEXUS_STORAGE_PATH=str(index), SCARF_ANALYTICS="false")
    cli = TOOLS / "gitnexus/node_modules/gitnexus/dist/cli/index.js"
    report('analyzer')
    stopped = threading.Event()
    def activity():
        path = run / 'analyze.log'
        try:
            with path.open('rb') as log:
                length = log.seek(0, os.SEEK_END)
                log.seek(max(0, length-2048))
                return {'log_bytes': length, 'output': log.read(2048).decode('utf-8', errors='replace')}
        except FileNotFoundError:return {'log_bytes': 0, 'output': ''}
    def heartbeat():
        while not stopped.wait(2):
            report('analyzer', **activity())
    ticker = threading.Thread(target=heartbeat, daemon=True)
    ticker.start()
    try:
        with (run / 'analyze.log').open('w', encoding='utf-8') as log:
            try:
                result = guarded_run([node_executable(), str(cli), 'analyze', str(snapshot), *GRAPH_FLAGS], cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, timeout=remaining(deadline,'analyzer',cancelled=cancelled), cancelled=cancelled, custody_path=base / 'graph-custody.json')
            finally:
                wait_custody(base / 'graph-custody.json', timeout=15)
    finally:
        stopped.set()
        ticker.join()
    report('validating', **activity())
    if result.returncode or source_state(deadline=deadline, **options) != before or graph_identity(deadline=deadline, cancelled=cancelled) != identity:
        raise RuntimeError("Graph failed or source changed; the previous manifest is preserved. See " + str(run / "analyze.log"))
    if not graph_storage_valid({'index': str(index), 'registry_home': str(home), 'snapshot': str(snapshot)}, base.resolve()):
        raise RuntimeError('Analyzer did not produce a complete index; see ' + str(run / 'analyze.log'))
    manifest = {**before, "snapshot": str(snapshot), "index": str(index), "registry_home": str(home),
                "identity": identity, "excluded_paths": list(GRAPH_EXCLUSIONS),
                "coverage": "syntactic mixed-platform graph; incomplete type references and runtime paths"}
    remaining(deadline,'manifest publication',cancelled=cancelled)
    tmp = base / "graph.json.tmp"
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    remaining(deadline,'manifest replacement',cancelled=cancelled)
    tmp.replace(base / "graph.json")
    report('ready', state='CURRENT')
    return graph_status(deadline=deadline, **options)


def source_state(deadline=None, cancelled=None) -> dict:
    check_cancelled(cancelled)
    if not (ROOT / ".local/workspace/context.json").is_file():
        raise RuntimeError("Run workspace setup for the selected checkout before analysis")
    digest = hashlib.sha256()
    workspace_files = [name for name in WORKSPACE_PATHS if (ROOT / name).exists()]
    for name in workspace_files:
        check_cancelled(cancelled)
        digest.update(name.encode() + b"\0" + (ROOT / name).read_bytes())
    for top in SOURCE_PATHS:
        if deadline is not None:remaining(deadline,'source fingerprint',cancelled=cancelled)
        path = ROOT / top
        files = sorted(path.rglob("*")) if path.is_dir() else [path]
        for item in files:
            if deadline is not None:remaining(deadline,'source fingerprint',cancelled=cancelled)
            if item.is_file() and not any(p.startswith(".") for p in item.relative_to(ROOT).parts):
                digest.update(item.relative_to(ROOT).as_posix().encode() + b"\0")
                digest.update(item.read_bytes())
    uncovered = []
    for directory, dirs, names in os.walk(ROOT):
        if deadline is not None:remaining(deadline,'source traversal',cancelled=cancelled)
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in names:
            if name.endswith(".go"):
                relative = (Path(directory) / name).relative_to(ROOT)
                if relative.parts[0] not in SOURCE_PATHS:
                    uncovered.append(relative.as_posix())
    def read_git(stage, *args):
        timeout=remaining(deadline,stage,20,cancelled=cancelled) if deadline is not None else 20
        if cancelled is None:return git(*args,timeout=timeout)
        return guarded_run([host()['git_executable'],'--no-pager','-c','core.fsmonitor=false',
            '-c','core.hooksPath=NUL','-C',str(ROOT),*args],stdin=subprocess.DEVNULL,
            capture_output=True,check=True,text=True,encoding='utf-8',timeout=timeout,
            cancelled=cancelled,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout.strip()
    head=read_git('source HEAD',"rev-parse", "HEAD")
    dirty=read_git('source status',"status", "--porcelain", "--untracked-files=all", "--", *SOURCE_PATHS, *WORKSPACE_PATHS)
    if deadline is not None:remaining(deadline,'source validation',cancelled=cancelled)
    return {"repo": str(ROOT), "head": head, "fingerprint": digest.hexdigest(),
            "uncovered_go": sorted(uncovered),
            "workspace_files": workspace_files,
            "dirty": dirty}


def cache_root() -> Path:
    key = hashlib.sha256(str(ROOT).casefold().encode()).hexdigest()[:16]
    return TOOLS / "cache" / "checkouts" / key


def build_env(profile: str, tags: str = "") -> dict:
    from package_map import build_environment
    env = build_environment("/".join(PROFILES[profile]), tags)
    env["XRAY_ANALYSIS_GIT"] = host()["git_executable"]
    if host().get("go"):
        env["XRAY_ANALYSIS_GO"] = host()["go"]
    return env


def graph_status(deadline=None, cancelled=None) -> dict:
    options = {'cancelled': cancelled} if cancelled is not None else {}
    state = source_state(deadline=deadline, **options) if deadline is not None else source_state(**options)
    identity = graph_identity(deadline=deadline, cancelled=cancelled)
    result = {"source": state, "identity": identity, "preparation": graph_progress()}
    path = cache_root() / "graph.json"
    if not path.exists():
        return {**result, "status": "MISSING"}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {**result, "status": "STALE", "reason": "Invalid manifest"}
    cache = cache_root().resolve()
    storage_valid = graph_storage_valid(manifest, cache)
    current = storage_valid and not state["dirty"] and not state["uncovered_go"] and not state["workspace_files"] and manifest.get("repo") == str(ROOT) and manifest.get("fingerprint") == state["fingerprint"] and manifest.get("identity") == identity
    return {**result, "status": "CURRENT" if current else "STALE", "manifest": manifest}


def node_executable() -> str:
    import shutil
    node = os.environ.get("XRAY_ANALYSIS_NODE") or host().get("node") or shutil.which("node")
    if not node:
        raise RuntimeError("Node is unavailable; configure XRAY_ANALYSIS_NODE on this host")
    return node


def remaining(deadline, stage, maximum=None, cancelled=None):
    check_cancelled(cancelled)
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError('Graph operation deadline exceeded during ' + stage)
    return min(value, maximum) if maximum is not None else value


def refresh_graph(deadline=None, cancelled=None, force=False, progress=None) -> dict:
    """Coalesce refreshes from concurrent MCP sessions for this checkout."""
    base = cache_root()
    base.mkdir(parents=True, exist_ok=True)
    lock = base / 'graph-refresh.lock'
    deadline = time.monotonic() + GRAPH_PREPARE_SECONDS if deadline is None else deadline
    options = {'cancelled': cancelled} if cancelled is not None else {}
    first = True
    initial = None
    # Kernel locks disappear on process exit, including crashes. Keep the file:
    # unlinking a flock file can let two waiters lock different inodes.
    with lock.open('a+b') as handle:
        while True:
            remaining(deadline, 'index lease',cancelled=cancelled)
            current = graph_status(deadline=deadline, **options)
            if first:
                initial = current.get('manifest', {}).get('index')
                first = False
            if current['status'] == 'CURRENT' and (not force or current['manifest']['index'] != initial):
                return current
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Graph refresh is still owned by another process: ' + str(lock))
                if progress:
                    owner = graph_progress()
                    progress({**owner, 'owner_phase': owner.get('phase'), 'phase': 'waiting_for_owner'})
                if cancelled is None:time.sleep(1)
                else:cancelled.wait(1)
        try:
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps({'pid': os.getpid(), 'repo': str(ROOT)}).encode())
            handle.flush()
            if force:
                # A previous owner can publish between our last unlocked read
                # and successful acquisition. Coalesce that completed force too.
                ready = graph_status(deadline=deadline, **options)
                if ready['status'] == 'CURRENT' and ready['manifest']['index'] != initial:
                    return ready
            extra = {}
            if force:extra['force'] = True
            if progress is not None:extra['progress'] = progress
            return _refresh_graph_unlocked(deadline=deadline, **options, **extra)
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def committed_source_paths(head, deadline=None, cancelled=None) -> tuple[str, ...]:
    """Select only covered roots present in the exact committed snapshot."""
    timeout = remaining(deadline, 'source archive roots', 20, cancelled=cancelled) if deadline is not None else 20
    result = guarded_run([host()['git_executable'], 'ls-tree', '-z', '--name-only', head, '--', *SOURCE_PATHS],
        cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, check=True, text=True, encoding='utf-8',
        timeout=timeout, cancelled=cancelled, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    tracked = set(result.stdout.split('\0'))
    selected = tuple(path for path in SOURCE_PATHS if path in tracked)
    if not selected:
        # An empty git archive path list would accidentally export all of HEAD.
        raise RuntimeError('No covered source roots exist at the selected source revision')
    return selected


def _refresh_graph_unlocked(deadline=None, cancelled=None, force=False, progress=None) -> dict:
    deadline = time.monotonic() + GRAPH_PREPARE_SECONDS if deadline is None else deadline
    options = {'cancelled': cancelled} if cancelled is not None else {}
    remaining(deadline,'refresh validation',cancelled=cancelled)
    status = graph_status(deadline=deadline, **options)
    if status["status"] == "CURRENT" and not force:
        return status
    before = status["source"]
    if before["dirty"]:
        raise RuntimeError("Graph refresh needs committed source. Use live gopls/AST evidence for uncommitted changes")
    if before["uncovered_go"]:
        raise RuntimeError("New Go source roots require an explicit graph export-scope update; use live gopls: " + str(before["uncovered_go"]))
    if before["workspace_files"]:
        raise RuntimeError("Graph export does not cover a go.work workspace; use live gopls until explicit multi-module coverage is accepted")
    base = cache_root()
    base.mkdir(parents=True, exist_ok=True)
    wait_custody(base / 'graph-custody.json', timeout=remaining(deadline, 'previous analyzer custody', cancelled=cancelled), cancelled=cancelled)
    previous = graph_progress()
    if not force and previous.get('state') == 'FAILED' and previous.get('key') == graph_key(status):
        raise RuntimeError('Previous graph preparation failed for this source/analyzer identity; inspect progress/log and use graph_prepare(force=true) to retry: ' + previous.get('error', 'unknown failure'))
    operation = {'preparation_id': uuid.uuid4().hex, 'pid': os.getpid(),
                 'key': graph_key(status), 'started_at': time.time(), 'state': 'PREPARING'}
    def report(phase, **details):
        operation.update(phase=phase, elapsed_seconds=round(time.time()-operation['started_at'], 3), **details)
        temporary = base / ('graph-progress.' + operation['preparation_id'] + '.tmp')
        temporary.write_text(json.dumps(operation), encoding='utf-8')
        temporary.replace(base / 'graph-progress.json')
        if progress:progress(operation.copy())
    try:
        return _build_graph(before, status['identity'], base, deadline, cancelled, report)
    except BaseException as error:
        from resource_guard import CancelledError
        report('cancelled' if isinstance(error, CancelledError) else 'failed',
               state='CANCELLED' if isinstance(error, CancelledError) else 'FAILED', error=str(error))
        raise


def packages(profile: str, package: str | None, tags: str) -> int:
    cache = cache_root()
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256((profile + ":" + tags + ":0").encode()).hexdigest()[:12]
    output = cache / ("packages-" + key + ".json")
    command = [sys.executable, str(SCRIPTS / "package_map.py"), "--repo", str(ROOT), "--out", str(output), "--platforms", "/".join(PROFILES[profile]), "--tags", tags]
    env = build_env(profile, tags)
    if package:
        probe = guarded_run(command + ["--impact", package], env=env, capture_output=True, text=True, encoding="utf-8") if output.exists() else None
        if probe and probe.returncode == 0:
            print(probe.stdout)
            return 0
    guarded_run(command, env=env, check=True, timeout=180)
    if package:
        guarded_run(command + ["--impact", package], env=env, check=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("status", "graph-status", "graph-refresh", "packages", "symbol"))
    parser.add_argument("--profile", choices=PROFILES, default="windows")
    parser.add_argument("--tags", default="")
    parser.add_argument("--package")
    parser.add_argument("--file")
    parser.add_argument("--symbol")
    parser.add_argument("--repo", type=Path, default=ROOT, help="Assert the installed checkout root")
    parser.add_argument("--out", type=Path, help="Fresh symbol inspection output directory")
    parser.add_argument("--force", action="store_true", help="Deliberately rebuild even a current graph")
    parser.add_argument("--prepare-seconds", type=int, default=GRAPH_PREPARE_SECONDS)
    args = parser.parse_args()
    if args.repo.resolve() != ROOT.resolve():
        parser.error("--repo must match this installed checkout; install the toolkit in the requested checkout")
    if args.mode == "status":
        print(json.dumps({"source": source_state(), "tools": str(TOOLS), "cache": str(cache_root()), "profile": {"GOOS": PROFILES[args.profile][0], "GOARCH": PROFILES[args.profile][1], "CGO_ENABLED": "0", "tags": args.tags}}, indent=2))
    elif args.mode == "graph-status":
        print(json.dumps(graph_status(), indent=2))
    elif args.mode == "graph-refresh":
        if not 1 <= args.prepare_seconds <= GRAPH_PREPARE_MAX_SECONDS:
            parser.error('--prepare-seconds must be between 1 and ' + str(GRAPH_PREPARE_MAX_SECONDS))
        print(json.dumps(refresh_graph(deadline=time.monotonic()+args.prepare_seconds, force=args.force,
              progress=lambda value: print(json.dumps(value), file=sys.stderr, flush=True)), indent=2))
    elif args.mode == "packages":
        return packages(args.profile, args.package, args.tags)
    else:
        if not args.file or not args.symbol:
            parser.error("symbol requires --file and --symbol")
        env = build_env(args.profile, args.tags)
        command = [sys.executable, str(SCRIPTS / "inspect_go.py"), "--repo", str(ROOT), "--tools", str(TOOLS), "--file", args.file, "--symbol", args.symbol, "--platform", "/".join(PROFILES[args.profile]), "--tags", args.tags]
        if args.out:
            command += ["--out", str(args.out)]
        return guarded_run(command, env=env).returncode
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
