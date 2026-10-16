"""Pinned gopls v0.23.0 stdio adapter: one-based reference locations."""
import argparse
import os
import pathlib
import re
import subprocess
import sys

from resource_guard import Relay, run


def normalize(message, kind):
    if kind == "initialize" and "result" in message:
        current = message["result"].get("instructions", "")
        message["result"]["instructions"] = current + "\nPinned gopls v0.23.0 for the selected Go workspace. Reference line numbers in go_symbol_references are normalized by this adapter to one-based source lines. Queries reflect only this server's GOOS/GOARCH build configuration; they do not prove runtime reachability or safe deletion. Use only the selected GOOS/GOARCH/CGO/tags profile and verify go_workspace matches the requested root."
    if kind == "go_symbol_references" and "result" in message:
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
    if not re.search(r"(?m)^golang.org/x/tools/gopls v0\.23\.0(?:\s|$)", version):
        raise RuntimeError("This adapter requires gopls v0.23.0 for its reference-line normalization")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    Relay([str(binary), "mcp"], root, env=env, transform=normalize, transient=transient).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
