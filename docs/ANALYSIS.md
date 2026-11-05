# Go and source analysis

Run the commands below from the explicitly selected Xray source root, after
[installation](INSTALLATION.md) and
`python .agents/scripts/workspace.py setup --analysis-tools D:/Tools/xray-analysis`.
The DevKit repository has no Go runtime to inspect. Replace the illustrative tools
path and stock source paths with the actual task inputs before invoking them.

The installed toolkit operates on the checkout containing its `.agents` directory.
Local context records the checkout, executable paths and tools directory; it is
host data and stays ignored.
The launchers never discover or borrow a different project's Python helper files.
`--repo` on `xray_analysis.py` and `xray_mcp.py` asserts the installed checkout
identity; it does not redirect those launchers to another source root. Install
the toolkit explicitly in another checkout before selecting it. Standalone
`package_map.py` and `inspect_go.py` accept an explicit module root instead.
The configured wrapper loads host context before parsing arguments, so even its
`--help` requires setup. Read its parser or use the standalone helper's `--help`
when investigating prerequisites before setup.

## Select only the evidence needed

Use package maps for import consumers, gopls for named symbol references and API
context, ast-grep for syntax patterns, and deadcode for a named reachability
question. Graphs provide supplementary call-chain leads. A small question does not
require every tool or a platform matrix.

```powershell
python .agents/scripts/xray_analysis.py status --repo . --profile windows
python .agents/scripts/xray_analysis.py packages --repo . --profile linux --package github.com/xtls/xray-core/transport
python .agents/scripts/xray_analysis.py symbol --repo . --profile android --file transport/link.go --symbol Link
python .agents/scripts/xray_analysis.py symbol --repo . --profile linux --file transport/link.go --symbol Link --out .local/analysis/inspection-001
```

These are alternatives, not a required sequence or build matrix. Add
`--tags actual_tag` only when the accepted task requires that real build tag.

Profiles select windows/amd64, linux/amd64 or android/arm64. Windows and Linux are
the supported hosts; Android here is an analysis target. Every selected profile
sets CGO_ENABLED=0, GOMAXPROCS=2, GOWORK=off and GOFLAGS=-mod=readonly plus explicitly
requested tags. An inherited parent workspace or GOFLAGS value cannot silently
change that profile. Local go.work files are included in fingerprints and prevent
a current graph claim because graph export covers a single module. Symbol and
package analysis explicitly inspect the selected module with GOWORK=off.

`python .agents/scripts/xray_mcp.py gopls --repo . --profile windows` launches the same profile through a
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
actual supported tool versions. Fresh provisioning selects gopls v0.24.0.
The adapter recognizes only qualified v0.23.0 and v0.24.0 binaries and reports the
actual selected version in MCP initialization. Version 0.24 reference prose is
already one-based and is preserved; only legacy 0.23 reference prose receives
one increment. Diagnostics retain upstream zero-based protocol coordinates and
other methods are unchanged. Unknown versions are refused before backend startup.
The compatibility path keeps retained 0.23 frontends usable after helper updates
or idle backend restart; it does not change the fresh dependency default. Setup
alone does not upgrade binaries. The selected root binds workspace/cwd and keeps
native cross-module lookup behavior; actual parent access still applies. This
host-tool qualification is not Xray runtime or source-Go acceptance.

An inspection stores raw MCP initialization/catalogue/call responses, stderr,
probe log, source/build provenance, exact parsed locations, file context and the
ast-grep outline. Read `inspection.json` first: it records consistency, selected
build, workspace confirmation and reference locations. `file_context` points to
the raw `go_file_context` response; it is not a separately inferred API contract.
Follow `raw_dir`, `outline_file` and `probe.log` for the evidence behind that
summary. Partial or unfamiliar reference prose fails explicitly and
retains raw evidence. Source changes during extraction prevent a consistent
result. Use an empty output directory; default directories are unique. A
`SOURCE_CHANGED` result needs a new consistent extraction before relying on it.

Standalone alternatives from the installed source root (the paths are
illustrative; create the ignored output parent first):

```powershell
New-Item -ItemType Directory -Force .local/analysis | Out-Null
python .agents/scripts/package_map.py --repo . --out .local/analysis/packages.json --platforms linux/amd64
python .agents/scripts/package_map.py --repo . --out .local/analysis/packages.json --platforms linux/amd64 --impact github.com/xtls/xray-core/transport
python .agents/scripts/inspect_go.py --repo . --tools D:/Tools/xray-analysis --platform linux/amd64 --file transport/link.go --symbol Link
```

The second package command consumes the first command's saved map with the same
root/profile/tags; a mismatched source SHA or fingerprint requires rebuilding.
`--impact` does not rebuild that map. `inspect_go.py` performs the MCP probe and
creates its call file automatically.

For a protocol-level investigation, supply your own reviewed `calls.json`, a JSON
array of objects with `name` and `arguments`, then use a fresh probe output path:

```powershell
python .agents/scripts/mcp_probe.py --exe python --cwd . --out .local/analysis/probe-001 --calls .local/analysis/calls.json --args .agents/scripts/go_mcp.py --binary D:/Tools/xray-analysis/bin/gopls.exe --repo .
```

Place `--args` last; all remaining values are backend arguments.
The probe reports backend error results with a nonzero exit status and saves the
raw result. It does not negotiate reverse client capabilities.

## Graph freshness and lifetime

```powershell
python .agents/scripts/xray_analysis.py graph-status --repo .
python .agents/scripts/xray_analysis.py graph-refresh --repo .
```

No graph indexing happens during setup or ordinary startup. A cold semantic MCP
call starts or joins preparation and returns `PREPARING` with a ticket preserving
its exact original tool and arguments. Call `graph_wait` with that ticket and
`timeout_seconds` at most 30 until it returns the actual original query result
or a concrete failure. Each wait is bounded separately from preparation (default
900 seconds, selectable up to 1200), so the client request limit does not become
the indexer deadline. Pending preparation is not a semantic answer. Retained completed/terminal tickets return
their cached original response, marked historical, even after later preparation;
terminal responses remain eligible for eviction at the bounded ticket capacity.

`graph_prepare(force=false, timeout_seconds=900)` starts or joins explicitly;
`graph_status` validates readiness and reports phase, elapsed time and log;
`graph_cancel(preparation_id=...)` cancels only this frontend's exact preparation.
Cancelling a wait leaves preparation running. Another frontend joins the existing
checkout lease; owner shutdown cancels its analyzer and releases the lease for
recovery. Analyzer launches
publish a durable nonce/birth-bound custody claim before spawning; the next owner
fences delayed launches and verifies the exact old tree is gone before admission.
This closes the frontend-death gap between lease release and descendant cleanup. `list_repos` is cheap inventory and never starts preparation or validates
semantic freshness. A failed source/analyzer identity is latched to prevent the
same automatic cold retry: inspect its failure/log and use `graph_prepare` with
`force=true` after correcting the cause. Force rebuilds a current graph too.

CLI preparation streams progress to stderr while the reported analyzer log grows:

```powershell
python .agents/scripts/xray_analysis.py graph-refresh --repo . --prepare-seconds 900
python .agents/scripts/xray_analysis.py graph-refresh --repo . --force
```

Manifests bind source bytes, export policy/schema, installed GitNexus version/build,
lockfile and selected tree-sitter/Ladybug artifacts. Cached size/mtime signatures
track ordinary installed updates; this is freshness identity, not full dependency
attestation. Cache roots use canonical checkout paths. Archive export includes only
covered roots present in the exact committed revision; an empty selection refuses
rather than exporting all of HEAD. Dirty source, uncovered Go roots and local
workspace files prevent a current claim until the relevant scope is accepted.
Missing/corrupt index storage also prevents readiness. Failed, cancelled or changed
source/analyzer preparation preserves the previous immutable manifest. Equal
source bytes permit documentation-only HEAD reuse with both source and current
validated HEAD visible in query provenance.

Graph queries reuse one backend for the current immutable generation, and validate
source/manifest after execution. Initialization, backend startup, catalogues and
queued requests retain total deadlines. Exact request cancellation and stalled
operation retirement affect only the owned frontend/descendants. Backends release
after idle time and replay initialization on demand. Catalogue-change notifications
invalidate caches without dropping the tool surface. Keepalive requests do not
retain heavy backends indefinitely. Start a fresh frontend after launcher edits.

## Managed resources and limits

Run local test/build commands through the bundled guard. From the DevKit root,
the Python example exercises toolkit helpers. The Go example requires the
installed source root and that actual package; select the check from the task.

```powershell
python .agents/scripts/resource_guard.py --timeout 120 -- python -m unittest discover -s .agents/scripts -p test_analysis_helpers.py
python .agents/scripts/resource_guard.py --timeout 120 -- go test ./common/buf
```

`python .agents/scripts/resource_guard.py --clean` is a separate recovery action
for inactive managed scratch, not a required step after every successful command.

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
