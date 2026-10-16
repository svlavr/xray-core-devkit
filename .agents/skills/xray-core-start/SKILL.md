---
name: xray-core-start
description: Initialize the explicitly selected Xray Core workspace and report exact branch, baseline, remotes, policy and dirty paths. Never starts an implementation or publication by itself.
---

# Selected source startup

Read the current root's `AGENTS.md`, applicable `AGENTS.override.md`,
`.agents/CODEX_PACK.md`, `docs/PROJECT_SCOPE.md`, `docs/WORKFLOW.md`, the human's
accepted task/contract and ignored `.local/workspace/context.json`.
Run `python .agents/scripts/check_core.py` from the explicitly configured root.
A toolkit-only root may report tools/settings without a Go module; do not claim
source/runtime readiness until the actual source and baseline are supplied.

An external worker with owner-generated `.local/workspace/worker.json` instead
verifies its recorded root/base/local queue and actual Go MCP workspace. It
never inherits the integrator's checkpoint/publication authority. Skills and
roles are edited in the selected checkout; setup generates ignored host config,
not a second editable tool copy or an automatic connection to another project.

Report cwd, branch/HEAD, adopted official pin, actual remotes, expected-branch
policy, authorized publication boundary and dirty paths. Startup checks local
configuration; it does not prove a live remote branch tip. When needed use
`remote_evidence.py` and preserve LIVE/REUSED/UNAVAILABLE provenance. Do not
replace a failed network observation with a local or cached SHA labeled fresh.

`check_core.py` also reports committed source accounting under `docs/WORKFLOW.md`.
Use `.agents/metrics/modules.json` and `.agents/metrics/source-size.json` supplied
for this source scope. Missing/uninitialized metrics and pending candidate bytes
stay explicit. Verify HEAD with its committed catalog, not dirty worktree rules;
pending work is not a verified new footprint. No fetch/build/index is required
for source accounting. No private catalog or product contract is implied.

Map the current native owner and accepted gap before bounded implementation.
Use supplied current contracts/evidence, not a historical framework by association.
Record owners/state/locks/interfaces/dependencies and validation/stop rules before
editing. Startup never starts another task, refreshes an index, runs a platform
matrix, fetches, commits, pushes or exports source.
