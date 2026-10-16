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
import time
import zipfile
from resource_guard import run as guarded_run, check_cancelled

from local_environment import ROOT, host, git
TOOLS = Path(host()["analysis_tools"])
SCRIPTS = Path(__file__).resolve().parent
SOURCE_PATHS = ("app", "common", "core", "features", "infra", "main", "measurement", "proxy", "testing", "transport", "go.mod", "go.sum")
WORKSPACE_PATHS = ("go.work", "go.work.sum")
PROFILES = {"windows": ("windows", "amd64"), "android": ("android", "arm64"), "linux": ("linux", "amd64")}


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
    path = cache_root() / "graph.json"
    if not path.exists():
        return {"status": "MISSING", "source": state}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    cache = cache_root().resolve()
    index = Path(manifest.get("index", "")).resolve()
    registry = Path(manifest.get("registry_home", "")).resolve()
    storage_valid = index.is_relative_to(cache) and registry.is_relative_to(cache) and index.is_dir() and (index / "meta.json").is_file() and (index / "lbug").exists() and (registry / "registry.json").is_file()
    current = storage_valid and not state["dirty"] and not state["uncovered_go"] and not state["workspace_files"] and manifest.get("repo") == str(ROOT) and manifest.get("fingerprint") == state["fingerprint"]
    return {"status": "CURRENT" if current else "STALE", "source": state, "manifest": manifest}


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


def refresh_graph(deadline=None, cancelled=None) -> dict:
    """Coalesce refreshes from concurrent MCP sessions for this checkout."""
    base = cache_root()
    base.mkdir(parents=True, exist_ok=True)
    lock = base / 'graph-refresh.lock'
    deadline = time.monotonic() + 180 if deadline is None else deadline
    options = {'cancelled': cancelled} if cancelled is not None else {}
    # Kernel locks disappear on process exit, including crashes. Keep the file:
    # unlinking a flock file can let two waiters lock different inodes.
    with lock.open('a+b') as handle:
        while True:
            remaining(deadline, 'index lease',cancelled=cancelled)
            current = graph_status(deadline=deadline, **options)
            if current['status'] == 'CURRENT':
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
                if cancelled is None:time.sleep(1)
                else:cancelled.wait(1)
        try:
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps({'pid': os.getpid(), 'repo': str(ROOT)}).encode())
            handle.flush()
            return _refresh_graph_unlocked(deadline=deadline, **options)
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


def _refresh_graph_unlocked(deadline=None, cancelled=None) -> dict:
    deadline = time.monotonic() + 180 if deadline is None else deadline
    options = {'cancelled': cancelled} if cancelled is not None else {}
    remaining(deadline,'refresh validation',cancelled=cancelled)
    status = graph_status(deadline=deadline, **options)
    if status["status"] == "CURRENT":
        return status
    before = status["source"]
    if before["dirty"]:
        raise RuntimeError("Graph refresh needs committed source. Use live gopls/AST evidence for uncommitted changes")
    if before["uncovered_go"]:
        raise RuntimeError("New Go source roots require an explicit graph export-scope update; use live gopls: " + str(before["uncovered_go"]))
    if before["workspace_files"]:
        raise RuntimeError("Graph export does not cover a go.work workspace; use live gopls until explicit multi-module coverage is accepted")
    archive_paths = committed_source_paths(before['head'], deadline=deadline, cancelled=cancelled)
    base = cache_root()
    base.mkdir(parents=True, exist_ok=True)
    # A unique output preserves earlier evidence and avoids partial-index reuse.
    run = Path(tempfile.mkdtemp(prefix="graph-", dir=base))
    snapshot = run / "source"
    snapshot.mkdir()
    archive = run / "source.zip"
    guarded_run([host()["git_executable"], "archive", "--format=zip", "--output=" + str(archive), before["head"], *archive_paths], cwd=ROOT, stdin=subprocess.DEVNULL, check=True, timeout=remaining(deadline,'source archive',20,cancelled=cancelled), cancelled=cancelled, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
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
    result = guarded_run([node_executable(), str(cli), "analyze", str(snapshot), "--skip-git", "--index-only", "--force", "--workers", "1"], cwd=ROOT, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=remaining(deadline,'analyzer',180,cancelled=cancelled), cancelled=cancelled)
    (run / "analyze.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    if result.returncode or source_state(deadline=deadline, **options) != before:
        raise RuntimeError("Graph failed or source changed; the previous manifest is preserved. See " + str(run / "analyze.log"))
    manifest = {**before, "snapshot": str(snapshot), "index": str(index), "registry_home": str(home),
                "excluded_paths": [".local", ".agents", ".codex", "untracked files"],
                "coverage": "syntactic mixed-platform graph; incomplete type references and runtime paths"}
    remaining(deadline,'manifest publication',cancelled=cancelled)
    tmp = base / "graph.json.tmp"
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    remaining(deadline,'manifest replacement',cancelled=cancelled)
    tmp.replace(base / "graph.json")
    return graph_status(deadline=deadline, **options)


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
    args = parser.parse_args()
    if args.repo.resolve() != ROOT.resolve():
        parser.error("--repo must match this installed checkout; install the toolkit in the requested checkout")
    if args.mode == "status":
        print(json.dumps({"source": source_state(), "tools": str(TOOLS), "cache": str(cache_root()), "profile": {"GOOS": PROFILES[args.profile][0], "GOARCH": PROFILES[args.profile][1], "CGO_ENABLED": "0", "tags": args.tags}}, indent=2))
    elif args.mode == "graph-status":
        print(json.dumps(graph_status(), indent=2))
    elif args.mode == "graph-refresh":
        print(json.dumps(refresh_graph(), indent=2))
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
