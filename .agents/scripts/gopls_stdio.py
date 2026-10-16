"""Compatibility entrypoint for the bundled version-checked gopls adapter.

Requires the same explicit --binary and --repo/--root arguments as go_mcp.py.
Reference normalization is performed once by that adapter.
"""
from go_mcp import main

if __name__ == "__main__":
    raise SystemExit(main())
