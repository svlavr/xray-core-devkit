"""Capture bounded JSON-lines MCP evidence using the bundled owner-safe client."""
import argparse
import json
import os
from pathlib import Path
import time

from mcp_backend import Backend


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", required=True)
    parser.add_argument("--args", nargs=argparse.REMAINDER, default=[], help="Backend arguments; place this option last")
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--calls", type=Path)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    args.out.mkdir(parents=True, exist_ok=True)
    backend = None
    with (args.out / "stderr.log").open("w", encoding="utf-8") as errors:
        try:
            started = time.perf_counter()
            backend = Backend([args.exe, *args.args], args.cwd.resolve(), os.environ.copy(), errors, timeout=args.timeout)
            (args.out / "initialize.json").write_text(json.dumps(backend.initialization, indent=2), encoding="utf-8")
            print(json.dumps({"initialize": backend.initialization.get("result", {}).get("serverInfo"),
                              "seconds": round(time.perf_counter() - started, 3)}), flush=True)
            requests = [("tools.json", "tools/list", {})]
            if args.calls:
                for index, call in enumerate(json.loads(args.calls.read_text(encoding="utf-8-sig"))):
                    name = call["name"]
                    if not isinstance(name, str) or not name or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in name):
                        raise ValueError("Call name must be a plain MCP tool identifier")
                    requests.append((str(index) + "-" + name + ".json", "tools/call", call))
            failed = False
            for sequence, (filename, method, params) in enumerate(requests, 1):
                started = time.perf_counter()
                result = backend.call({"jsonrpc": "2.0", "id": sequence, "method": method, "params": params})
                (args.out / filename).write_text(json.dumps(result, indent=2), encoding="utf-8")
                error = bool(result.get("error") or result.get("result", {}).get("isError") or "result" not in result)
                failed = failed or error
                print(json.dumps({"call": params.get("name", method), "seconds": round(time.perf_counter() - started, 3),
                    "isError": result.get("result", {}).get("isError"), "error": result.get("error"),
                    "saved": str(args.out / filename)}), flush=True)
            return 1 if failed else 0
        finally:
            if backend is not None:
                backend.close(force=True)


if __name__ == "__main__":
    raise SystemExit(main())
