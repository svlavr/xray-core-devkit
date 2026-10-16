---
name: xray-code-analysis
description: Analyze Go ownership, references, dependency impact and removal candidates in Xray Core using the installed Windows toolset. Use for understanding or simplifying shared Xray code; this skill does not authorize implementation or choose a runtime architecture.
---

# Xray code analysis

Use the current repository instructions and accepted scope. This is an analysis
workflow, not a second fork plan. Do not change source merely because a tool
reports an unused symbol, a missing graph edge, or a low impact score.

## Start with the question

Choose the smallest evidence set that answers the question:

- Package boundaries/import consumers: checkout-scoped `xray_analysis.py packages`.
- A named type, field or method and its consumers: gopls semantic references,
  definitions/implementations as needed, and reachable source owners.
- Syntax shapes (Link literals, Reader assignments, signatures): ast-grep.
- Why a function is reachable or which functions are candidates for removal:
  deadcode RTA with explicit executable/test roots.
- Visual browsing or call-chain leads: the existing graph index.
- Named unresolved value-flow question: consider CodeQL only after ordinary
  source/semantic analysis establishes the gap and its installation/licensing
  scope is resolved.

Do not run every tool or a full platform matrix for an ordinary local lookup.
Do not add another index, analyzer or framework after an unexplained result;
first check the selected file/symbol, build configuration and index freshness.

## Quick symbol inspection in the selected checkout

Use a fresh output directory; omitting --out creates one automatically.

Tools live outside the checkout at the installed host context's analysis-tools root.
The project launcher resolves its own checkout. Run from that repository root;
do not use another worktree's cached MCP cwd or graph.

```powershell
python .agents/scripts/xray_analysis.py symbol --file transport/link.go --symbol Link --profile windows
python .agents/scripts/xray_analysis.py packages --package github.com/xtls/xray-core/transport --profile android
```

The helper produces `inspection.json`, semantic reference locations, raw MCP
responses, a cross-file API context and an ast-grep file outline. It records
HEAD, a Go-source fingerprint and the selected platform; `SOURCE_CHANGED`
means the combined evidence is not consistent. It reads saved disk files.

The configured `xray_gopls_windows` and opt-in `xray_gopls_android` profiles can
be used directly when their tools are available. Confirm `go_workspace` matches this checkout once per
task/profile. Profiles explicitly use CGO=0 and no extra tags. For Linux or extra
tags, use `--profile linux` / `--tags` in the CLI. The pinned adapter converts gopls v0.23.0 reference
line prose to one-based lines. Do not apply that correction a second time.
The MCP subset does not expose all gopls LSP operations; use the installed
native gopls CLI/LSP for an exact implementation or hierarchy query when needed.

## Structural search

The dependency lock pins ast-grep 0.45.3. Provisioning places its Windows binary
at `<analysis-tools-root>/bin/ast-grep.exe`; confirm that installation before use.
Use read-only `run`, `scan` and `outline`; validate a query on a known positive
case before treating zero matches as evidence. No rewrites are implied.
The PowerShell examples use an illustrative tools root: replace its value with
the installed host context's actual `analysis_tools` path. `&` invokes the
executable at the constructed, quoted path.

```powershell
$analysisTools = 'D:/Tools/xray-analysis'
& "$analysisTools/bin/ast-grep.exe" run --lang Go --pattern 'transport.Link { $$$FIELDS }' --json=compact app/dispatcher/default.go
& "$analysisTools/bin/ast-grep.exe" run --lang Go --pattern '$LINK.Reader = $VALUE' --json=compact app/dispatcher/default.go
```

These identify syntax, not symbol identity: aliases, other types named Link,
embedded fields and other assignment forms require separate checks. Go call
patterns may need an enclosing function context to parse as calls. `outline`
is alpha and has no type/reference/call resolution; Go methods stay at file
level. Do not replace semantic references or ordinary text searches with it.

## Reachability

The dependency lock selects deadcode from x/tools v0.50.0 and Go 1.27.0.
Provisioning places the Windows binary at
`<analysis-tools-root>/bin/deadcode.exe`; a lock entry alone does not prove it is
installed or that an existing executable was built with that toolchain.

Run it only when reachability is the question. Prefer a clean committed source
snapshot outside the checkout for whole-program scans. State GOOS, GOARCH,
CGO, tags, package roots, test-root inclusion and generated-report policy.
Use bounded time/memory and keep cache-heavy executions serialized.

```powershell
$analysisTools = 'D:/Tools/xray-analysis'
& "$analysisTools/bin/deadcode.exe" -json ./main
& "$analysisTools/bin/deadcode.exe" -test -json ./...
& "$analysisTools/bin/deadcode.exe" -json -whylive=github.com/xtls/xray-core/core.New ./main
```

The binary uses RTA; VTA is not a deadcode mode. `-whylive` shows one preferred
path, not every caller. Generated functions and marker methods are excluded
from the report by default, although generated code participates in analysis.

A CLI/test-root result does not include external application or binding consumers.
For exposed APIs, mark external-consumer coverage unknown until the accepted
contract and exact reachable consumers are checked. Assembly, go:linkname,
plugins/foreign calls, other builds and interface obligations need separate
source review. Even an intersection of platform reports is not deletion proof.

## Freshness and result contract

Graph snapshots are supplementary. Project caches are keyed by canonical checkout;
their manifest records HEAD, a source fingerprint, excluded paths and coverage.
Run `python .agents/scripts/xray_analysis.py graph-status` when graph evidence is
needed. On MISSING/STALE with committed source, run `graph-refresh` automatically
on demand and retry that MCP call; it opens the new manifest automatically and
reuses its backend for subsequent queries. No startup refresh is performed.
Dirty source uses live gopls/AST; a committed graph must not answer as current.
Missing cache storage, new uncovered Go roots and go.work workspaces also prevent
a current graph claim. Multi-module graph coverage requires a named scope update;
use live semantic evidence in the meantime.
Equal source bytes permit reuse across a documentation-only HEAD change, with
both source HEAD and current validated HEAD visible. Old experimental snapshots
remain historical and are not the active project index.
Generic graphs may misbind platform-specific calls; inspect the selected build.
A graph's `exact` label is not a complete reference inventory.

For a proposed removal/move, return: exact owner and consumers, affected
contracts/tests, intended additions and actual eliminated responsibility,
source/build/index provenance, tool limitations, and unresolved boundaries.
Git co-change is a historical hint, not a dependency or test-coverage proof.
Behavior and test selection follow the existing accepted project plan; do not
manufacture a new ten-step gate or imply device/release validation.

Only after implementation is independently authorized, apply the project's
implementation, validation, review and checkpoint workflow. This skill grants
no runtime edits, deletion, architecture choice, public upload or publication.
