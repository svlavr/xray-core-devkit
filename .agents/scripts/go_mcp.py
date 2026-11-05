"""Qualified gopls v0.23.0/v0.24.0 adapter with versioned reference conventions."""
import argparse
import os
import pathlib
import re
import subprocess
import sys

from resource_guard import Relay, run


def normalize(message, kind, actual_version="v0.24.0"):
    if kind == "initialize" and "result" in message:
        current = message["result"].get("instructions", "")
        references = ("go_symbol_references prose is normalized by this adapter to one-based source lines. "
                      if actual_version == "v0.23.0" else "go_symbol_references prose uses native one-based source lines. ")
        message["result"]["instructions"] = current + "\nQualified gopls " + actual_version + " for the selected Go workspace. " + references + "Diagnostic protocol coordinates remain zero-based. Queries reflect only this server's GOOS/GOARCH build configuration; they do not prove runtime reachability or safe deletion. Use only the selected GOOS/GOARCH/CGO/tags profile and verify go_workspace matches the requested root. The selected root binds cwd/workspace, not a filesystem sandbox for native cross-module lookups."
    if actual_version == "v0.23.0" and kind == "go_symbol_references" and "result" in message:
        for item in message["result"].get("content", []):
            if item.get("type") == "text":
                item["text"] = re.sub(r"(?m)^(The reference is located on line )(\d+)(, which has content )",
                    lambda match: match[1] + str(int(match[2]) + 1) + match[3], item["text"])
    return message


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=pathlib.Path, required=True)
    parser.add_argument("--root", "--repo", dest="root", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    binary, root = args.binary.resolve(), args.root.resolve()
    if not binary.is_file() or not (root / "go.mod").is_file():
        parser.error("Expected an installed gopls and an explicit Go module root")
    transient = root / ".local/host/transient"
    env = {**os.environ, "GOWORK": "off"}
    version = run([str(binary), "version"], transient=transient, capture_output=True,
        check=True, text=True, encoding="utf-8", timeout=10, env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    qualified = re.search(r"(?m)^golang.org/x/tools/gopls (v0\.(?:23|24)\.0)(?:\s|$)", version)
    if not qualified:
        raise RuntimeError("This adapter requires qualified gopls v0.23.0 or v0.24.0 location conventions")
    actual_version = qualified[1]
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    Relay([str(binary), "mcp"], root, env=env, transform=lambda message, kind: normalize(message, kind, actual_version), transient=transient).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
