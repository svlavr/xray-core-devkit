"""Read-only Go symbol inspection with bundled MCP helpers and configured binaries."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from package_map import build_environment, git, source_fingerprint
from resource_guard import run

SCRIPTS = Path(__file__).resolve().parent


def parse_references(response):
    text = "\n".join(item.get("text", "") for item in response["result"].get("content", []) if item.get("type") == "text")
    locations = [{"file": filename, "line": int(line)} for filename, line in re.findall(
        r"Located in the file: (.*?)\nThe reference is located on line (\d+),", text)]
    reported = re.search(r"The object has (\d+) references", text)
    if not reported or len(locations) != int(reported[1]):
        raise RuntimeError("Reference response was not fully parsed; inspect raw evidence")
    return locations


def workspace_matches(response, repo):
    text = "\n".join(item.get("text", "") for item in response.get("result", {}).get("content", []) if item.get("type") == "text")
    selected, text = str(repo.resolve()).replace("\\", "/"), text.replace("\\", "/")
    if os.name == "nt":
        selected, text = selected.casefold(), text.casefold()
    return bool(re.search(re.escape(selected) + r"(?:[/\s\"'`]|$)", text))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--tools", type=Path, help="Configured analysis_tools root; otherwise read local context")
    parser.add_argument("--file", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--platform", choices=["windows/amd64", "android/arm64", "linux/amd64"], default="windows/amd64")
    parser.add_argument("--tags", default="")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    target = (repo / args.file).resolve()
    if not (repo / "go.mod").is_file() or not target.is_relative_to(repo) or target.suffix != ".go" or not target.is_file():
        parser.error("Target must be an existing Go file inside the selected module root")
    tools = args.tools
    if tools is None:
        context = json.loads((repo / ".local/workspace/context.json").read_text(encoding="utf-8"))
        if Path(context["core"]).resolve() != repo:
            raise RuntimeError("Host context belongs to another checkout")
        tools = Path(context["analysis_tools"])
    tools = tools.resolve()
    binary = tools / "bin" / ("gopls.exe" if os.name == "nt" else "gopls")
    ast = tools / "bin" / ("ast-grep.exe" if os.name == "nt" else "ast-grep")
    if not binary.is_file() or not ast.is_file():
        raise RuntimeError("Configured analysis_tools is missing gopls or ast-grep")
    before, fingerprint = git(repo, "rev-parse", "HEAD"), source_fingerprint(repo)
    out = args.out or tools / "inspections" / before[:8] / (uuid.uuid4().hex[:8] + "-" + target.stem)
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("Output directory must be empty; omit --out for a fresh inspection")
    out.mkdir(parents=True, exist_ok=True)
    calls = [{"name": "go_workspace", "arguments": {}},
        {"name": "go_symbol_references", "arguments": {"file": target.as_posix(), "symbol": args.symbol}},
        {"name": "go_file_context", "arguments": {"file": target.as_posix()}}]
    call_file = out / "calls.json"
    call_file.write_text(json.dumps(calls, indent=2), encoding="utf-8")
    env = build_environment(args.platform, args.tags)
    started = time.perf_counter()
    adapter = [str(SCRIPTS / "go_mcp.py"), "--binary", str(binary), "--repo", str(repo)]
    probe = run([sys.executable, str(SCRIPTS / "mcp_probe.py"), "--exe", sys.executable,
        "--cwd", str(repo), "--out", str(out / "raw"), "--calls", str(call_file), "--args", *adapter],
        env=env, transient=repo / ".local/host/transient", capture_output=True, text=True, encoding="utf-8", timeout=180)
    (out / "probe.log").write_text(probe.stdout + "\n" + probe.stderr, encoding="utf-8")
    if probe.returncode:
        raise RuntimeError("gopls probe failed; see " + str(out / "probe.log"))
    responses = []
    for filename in ("0-go_workspace.json", "1-go_symbol_references.json", "2-go_file_context.json"):
        value = json.loads((out / "raw" / filename).read_text(encoding="utf-8"))
        if value.get("error") or value.get("result", {}).get("isError") or "result" not in value:
            raise RuntimeError("MCP call failed: " + filename + "; inspect raw evidence")
        responses.append(value)
    if not workspace_matches(responses[0], repo):
        raise RuntimeError("UNKNOWN_WORKSPACE: go_workspace did not confirm the selected root; inspect raw evidence")
    locations = parse_references(responses[1])
    outline = run([str(ast), "outline", str(target), "--items", "all", "--view", "expanded", "--json=compact"],
        env=env, transient=repo / ".local/host/transient", capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
    (out / "outline.json").write_text(outline.stdout, encoding="utf-8")
    after, after_hash = git(repo, "rev-parse", "HEAD"), source_fingerprint(repo)
    report = {"status": "CONSISTENT" if (before, fingerprint) == (after, after_hash) else "SOURCE_CHANGED",
        "repo": str(repo), "source_sha": before, "source_fingerprint": fingerprint, "platform": args.platform,
        "build_environment": {key: env[key] for key in ("GOOS", "GOARCH", "CGO_ENABLED", "GOWORK", "GOFLAGS")},
        "saved_files_only": True, "workspace_verified": True, "target": {"file": str(target), "symbol": args.symbol},
        "semantic_references": {"count": len(locations), "include_declarations": True, "locations": locations},
        "outline_file": str(out / "outline.json"), "file_context": str(out / "raw/2-go_file_context.json"),
        "raw_dir": str(out / "raw"), "seconds": round(time.perf_counter() - started, 3),
        "limitations": ["Build-scoped semantic references; not runtime reachability.",
            "Outline is syntactic and alpha; not type or dependency resolution.",
            "External consumers and other build tags are not proven.",
            "No deletion or architecture choice is authorized by this report."]}
    (out / "inspection.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "references": len(locations), "platform": args.platform,
        "seconds": report["seconds"], "report": str(out / "inspection.json")}, indent=2))
    return 0 if report["status"] == "CONSISTENT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
