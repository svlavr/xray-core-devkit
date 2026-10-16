# Go and source analysis

The installed toolkit operates on the checkout containing `.agents`. Run workspace
setup first with an explicit `analysis_tools` directory. Local context records the
checkout, executable paths and tools directory; it is host data and stays ignored.
The launchers never discover or borrow a different project's Python helper files.
`--repo` on the checkout launchers asserts the installed checkout identity. Install
the toolkit in another checkout before selecting that checkout.

## Select only the evidence needed

Use package maps for import consumers, gopls for named symbol references and API
context, ast-grep for syntax patterns, and deadcode for a named reachability
question. Graphs provide supplementary call-chain leads. A small question does not
require every tool or a platform matrix.

```powershell
python .agents/scripts/xray_analysis.py status --repo . --profile windows
python .agents/scripts/xray_analysis.py packages --repo . --profile linux --package github.com/xtls/xray-core/transport
python .agents/scripts/xray_analysis.py symbol --repo . --profile android --file transport/link.go --symbol Link
python .agents/scripts/xray_analysis.py symbol --repo . --profile linux --tags selected --file transport/link.go --symbol Link --out .local/analysis/inspection-001
```

Profiles select windows/amd64, linux/amd64 or android/arm64. Windows and Linux are
the supported hosts; Android here is an analysis target. Every selected profile
sets CGO_ENABLED=0, GOMAXPROCS=2, GOWORK=off and GOFLAGS=-mod=readonly plus explicitly
requested tags. An inherited parent workspace or GOFLAGS value cannot silently
change that profile. Local go.work files are included in fingerprints and prevent
a current graph claim because graph export covers a single module. Symbol and
package analysis explicitly inspect the selected module with GOWORK=off.

`xray_mcp.py gopls --repo . --profile windows` launches the same profile through a
version-checked adapter. Confirm the actual `go_workspace` result before using
semantic evidence; launcher identity alone does not prove the backend loaded the
requested module. Symbol inspections check that returned workspace text identifies
the selected root and refuse an unrecognized result as UNKNOWN_WORKSPACE.

## Bundled helper chain

`xray_analysis.py packages` calls bundled `package_map.py`. That helper runs guarded
Go list, keeps production and test import edges separately, excludes synthesized
Go test packages, and records source SHA, full Go-source fingerprint, selected
platforms, tags and GOWORK. Cached impact queries reject source, root or profile
mismatches. Reverse imports are package dependencies, not symbol-use evidence.
`package_present=false` distinguishes an absent package from a package with no
consumers in this extraction.

`xray_analysis.py symbol` calls bundled `inspect_go.py`, then `mcp_probe.py`, then
`go_mcp.py`. `gopls_stdio.py` is a compatibility entrypoint to the same adapter and
requires explicit `--binary` and `--repo`/`--root`. The helper chain uses the
configured tools directory only for binaries and graph dependencies:

- `bin/gopls.exe` on Windows or `bin/gopls` on Linux.
- `bin/ast-grep.exe` on Windows or `bin/ast-grep` on Linux.
- `gitnexus/node_modules/gitnexus/dist/cli/index.js` for graph analysis and MCP.

Direct `go_mcp.py` and `gopls_stdio.py` invocation also forces GOWORK=off for the
version check and backend, while preserving the caller's GOOS, GOARCH, CGO and
GOFLAGS selection.

Git uses the recorded executable path through the checkout launcher. Go uses
XRAY_ANALYSIS_GO or PATH; an optional host context `go` value takes precedence
through that launcher. Standalone helpers allow XRAY_ANALYSIS_GO and
XRAY_ANALYSIS_GIT; otherwise they resolve those executable names through PATH.
Node selection is XRAY_ANALYSIS_NODE first,
then the host context's recorded `node`, then PATH. The dependency lock records the
actual supported tool versions. The gopls adapter specifically requires v0.23.0:
that release's reference-line prose uses zero-based locations, which the adapter
converts once to one-based lines. Other methods and prose are preserved. A new
gopls version requires reviewing that correction before changing the pin.

An inspection stores raw MCP initialization/catalogue/call responses, stderr,
probe log, source/build provenance, exact parsed locations, file context and the
ast-grep outline. Partial or unfamiliar reference prose fails explicitly and
retains raw evidence. Source changes during extraction prevent a consistent
result. Symbol output directories must be fresh; default directories are unique.

Standalone examples (the tools path is illustrative and supplied by the caller):

```powershell
python .agents/scripts/package_map.py --repo . --out .local/analysis/packages.json --platforms linux/amd64 --tags selected
python .agents/scripts/package_map.py --repo . --out .local/analysis/packages.json --platforms linux/amd64 --tags selected --impact github.com/xtls/xray-core/transport
python .agents/scripts/inspect_go.py --repo . --tools <analysis-tools> --platform linux/amd64 --file transport/link.go --symbol Link
python .agents/scripts/mcp_probe.py --exe python --cwd . --out .local/analysis/probe --calls .local/analysis/calls.json --args .agents/scripts/go_mcp.py --binary <analysis-tools>/bin/gopls.exe --repo .
```

Place `mcp_probe.py --args` last; all remaining values are backend arguments.
The probe reports backend error results with a nonzero exit status and saves the
raw result. It does not negotiate reverse client capabilities.

## Graph freshness and lifetime

```powershell
python .agents/scripts/xray_analysis.py graph-status --repo .
python .agents/scripts/xray_analysis.py graph-refresh --repo .
```

No graph indexing happens during setup or ordinary startup. The graph MCP checks
freshness on demand and refreshes missing/stale committed source before the first
query. Dirty source uses live semantic/AST evidence. Uncovered Go roots and local
workspace files refuse graph refresh until export coverage is explicitly updated.
Cache identities use canonical checkout paths; manifests record source fingerprint,
source HEAD, snapshot, index, registry and limited graph coverage. Equal source
bytes permit reuse across a documentation-only HEAD change; query provenance shows
both source HEAD and the current validated HEAD. Missing index storage prevents a
current claim. Failed, cancelled or changed-source refreshes preserve the previous
manifest. An OS lease coalesces concurrent refresh requests.

Graph queries reuse a backend only for the current immutable index generation.
Source and manifest are checked again after a query. Initialization, backend
startup, catalogue reads and queued work have total deadlines. Exact queued and
active cancellation is scoped to that request; stalled uncooperative operations
retire their owned frontend and descendants. Backends release after idle time and
replay initialization when needed. Catalogue-change notifications invalidate the
cache without dropping the tool surface. Keepalive control requests do not retain
heavy backends indefinitely.

## Managed resources and limits

Run local test/build commands through the bundled guard:

```powershell
python .agents/scripts/resource_guard.py --timeout 120 -- python -m unittest discover -s .agents/scripts -p test_analysis_helpers.py
python .agents/scripts/resource_guard.py --timeout 120 -- go test ./common/buf
python .agents/scripts/resource_guard.py --clean
```

Each managed command owns its descendant tree and isolated marked scratch under
`.local/host/transient`. Normal exit, error, timeout and owner death reap that tree.
Recovery removes only inactive marked runs after checking the lease; foreign,
active, locked and redirected paths remain intact. Shared Go caches and evidence
outside scratch remain available. Owner cleanup never kills processes by name or
purges global TEMP. Commands producing lasting artifacts must write outside the
managed scratch directory.

Semantic evidence is build-scoped and reads saved files. Graph edges are
mixed-platform and incomplete; an edge labelled exact is not a complete consumer
inventory. AST outlines are syntactic and alpha. Deadcode roots, test inclusion,
CGO/tags, foreign/binding consumers and generated-source policy must be stated
for a reachability claim. None of these reports alone proves safe removal,
external-consumer compatibility, device behavior or runtime performance.
