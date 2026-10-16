"""Build-scoped Go import maps and conservative reverse-import evidence."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from resource_guard import run


def source_fingerprint(repo):
    digest = hashlib.sha256()
    files = [repo / name for name in ("go.mod", "go.sum", "go.work", "go.work.sum") if (repo / name).exists()]
    for directory, dirs, names in os.walk(repo):
        dirs[:] = [name for name in dirs if not name.startswith(".")]
        files.extend(Path(directory) / name for name in names if name.endswith(".go"))
    for path in sorted(files):
        digest.update(path.relative_to(repo).as_posix().encode() + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def build_environment(platform, tags=""):
    goos, arch = platform.split("/")
    if (goos, arch) not in (("windows", "amd64"), ("android", "arm64"), ("linux", "amd64")):
        raise ValueError("Unsupported analysis build profile: " + platform)
    env = os.environ.copy()
    env.update(GOOS=goos, GOARCH=arch, CGO_ENABLED="0", GOWORK="off", GOMAXPROCS="2",
               GOFLAGS="-mod=readonly" + (" -tags=" + tags if tags else ""))
    return env


def git(repo, *args):
    # No shared host Python helper is needed; configured binaries are optional
    # for direct standalone invocation and otherwise resolved from PATH.
    binary = os.environ.get("XRAY_ANALYSIS_GIT", "git")
    return run([binary, "--no-pager", "-c", "core.fsmonitor=false", "-c",
                "core.hooksPath=" + os.devnull, "-C", str(repo), *args],
               transient=repo / ".local/host/transient", capture_output=True,
               text=True, encoding="utf-8", check=True, timeout=20).stdout.strip()


def parse_packages(text):
    decoder, pos, packages = json.JSONDecoder(), 0, []
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos == len(text):
            break
        item, pos = decoder.raw_decode(text, pos)
        path = item.get("ImportPath", "")
        if item.get("ForTest") or "[" in path or path.endswith(".test"):
            continue
        packages.append({"path": path, "name": item["Name"], "dir": item.get("Dir"),
            "imports": item.get("Imports", []), "test_imports": item.get("TestImports", []),
            "external_test_imports": item.get("XTestImports", []), "go_files": item.get("GoFiles", []),
            "ignored_go_files": item.get("IgnoredGoFiles", []), "incomplete": item.get("Incomplete", False)})
    return packages


def impact_reports(data, package):
    for build in data["builds"]:
        reverse, production, tests = (collections.defaultdict(set) for _ in range(3))
        for item in build["packages"]:
            for imported in item["imports"]:
                reverse[imported].add(item["path"])
                production[imported].add(item["path"])
            for imported in item["test_imports"] + item["external_test_imports"]:
                reverse[imported].add(item["path"])
                tests[imported].add(item["path"])
        visited, todo = {package}, [package]
        while todo:
            for dep in reverse[todo.pop()]:
                if dep not in visited:
                    visited.add(dep)
                    todo.append(dep)
        yield {"platform": build["platform"], "package": package,
            "package_present": any(item["path"] == package for item in build["packages"]),
            "direct": sorted(reverse[package] - {package}),
            "direct_production": sorted(production[package] - {package}),
            "direct_test": sorted(tests[package] - {package}), "transitive": sorted(visited - {package}),
            "scope": "package imports including test imports; not symbol references or runtime reachability"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--platforms", nargs="+", default=["windows/amd64"])
    parser.add_argument("--tags", default="")
    parser.add_argument("--impact")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    if not (repo / "go.mod").is_file():
        parser.error("--repo must select a Go module root")
    for platform in args.platforms:
        build_environment(platform, args.tags)
    sha, fingerprint = git(repo, "rev-parse", "HEAD"), source_fingerprint(repo)
    if args.impact:
        data = json.loads(args.out.read_text(encoding="utf-8"))
        if (sha != data["source_sha"] or fingerprint != data["source_fingerprint"]
                or str(repo) != data.get("source_cwd") or args.tags != data.get("tags", "")
                or args.platforms != [item["platform"] for item in data["builds"]]
                or data.get("gowork") != "off"):
            raise RuntimeError("STALE package map; rebuild for the selected source/build profile")
        for report in impact_reports(data, args.impact):
            print(json.dumps(report, indent=2))
        return 0
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all", "--", "*.go", "go.mod", "go.sum", "go.work", "go.work.sum").splitlines()
    result = {"source_fingerprint": fingerprint, "source_sha": sha, "source_cwd": str(repo),
        "tracked_source_dirty": dirty, "tags": args.tags, "gowork": "off",
        "scope": "Go package imports and test imports for selected builds; not runtime reachability or symbol use", "builds": []}
    for platform in args.platforms:
        started = time.perf_counter()
        proc = run([os.environ.get("XRAY_ANALYSIS_GO", "go"), "list", "-mod=readonly", "-test", "-json", "./..."],
            cwd=repo, env=build_environment(platform, args.tags), transient=repo / ".local/host/transient",
            capture_output=True, text=True, encoding="utf-8", check=True, timeout=180)
        packages = parse_packages(proc.stdout)
        build = {"platform": platform, "cgo_enabled": False, "packages": packages,
                 "seconds": round(time.perf_counter() - started, 3)}
        result["builds"].append(build)
        print(json.dumps({"platform": platform, "packages": len(packages),
            "import_edges": sum(len(item["imports"]) for item in packages), "seconds": build["seconds"]}), flush=True)
    if git(repo, "rev-parse", "HEAD") != sha or source_fingerprint(repo) != fingerprint:
        raise RuntimeError("Source changed during extraction; output not saved")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
