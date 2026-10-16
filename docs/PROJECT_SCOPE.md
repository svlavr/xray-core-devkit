# Supplying a project scope

The devkit distributes the complete configured Xray Codex workflow: eleven
skills, eight named roles, Windows analysis/session helpers, source accounting,
filtered export/CI, and optional Gas City/Beads workers. It is an independent
public tooling project. It contains no product runtime, proprietary module
contracts, project stage history, source acceptance or publication destination.
It does not have to support arbitrary platforms or unrelated projects.

Installing or inspecting it does not connect any existing checkout. The human
chooses whether and where to integrate it. Use the selected checkout's current
files and instructions; historical snapshots are evidence only when explicitly
named. Never copy another project's runtime, private plans, credentials, raw
captures or history as a substitute for missing input.

Before source work, main records these concrete inputs in the task or a named
owner-approved scope document:

- Canonical source root, permitted worktrees and exact branch/HEAD.
- Official upstream URL/ref and adopted immutable baseline for comparisons.
- Required behavior, trigger, caller/consumer, success/failure meaning and
  compatibility requirements; identify the actual contract path or supplied text.
- Read set, exact write set, dirty exclusions and integration owner.
- Work mode: read-only research, accepted implementation, artifact validation,
  review, handoff, or toolkit maintenance.
- Observable acceptance, required test/build configuration, validation executor,
  time/resource bounds and stop conditions.
- Separately authorized Git behavior: no checkpoint, local checkpoint, or commit
  plus non-force push to an exact remote/ref. A task may explicitly save an
  automatic checkpoint policy; this devkit does not supply one by default.
- Allowed external inputs/disclosure and any export/CI destination and allowlist.

No fixed module list or stage machine is implied. The human's current task and
its accepted contract own scope. Read-only research produces evidence/proposals;
it does not grant edits. A consumer's integration task does not authorize source
fork changes: report an alleged gap with exact revisions, current APIs/adapters,
required behavior and the smallest proposal, then obtain source-owner authority.

Toolkit-only tasks can use this repository as their task root without pretending
it is a Go module. Go analysis, runtime implementation, Android validation and
source publication remain unavailable until their actual source/artifact inputs
exist. Missing prerequisites are explicit `NEEDS_CONTEXT`/`BLOCKED` outcomes,
not empty inventories, fabricated success or grounds for weaker tests.

Host setup writes ignored `.local/workspace/context.json` for the explicitly
selected root and analysis-tools installation. A prepared external worker also
uses `.local/workspace/worker.json` with its exact base/local queue. Check the
actual Go MCP `go_workspace` once per task/profile; a host identity report alone
does not prove its source root. Fresh sessions adopt changed role/launcher config.

For source-size accounting, the owner supplies/reviews `.agents/metrics/modules.json`
and an exact upstream baseline before initializing
`.agents/metrics/source-size.json`. The catalog describes this source project's
actual ownership; it must not recreate private module names or count a shared
path twice. See `WORKFLOW.md` for accounting and checkpoint rules.

Filtered public source export additionally requires an owner-supplied
`.agents/public-export.json` reviewed against the selected source and exact
public destination. Read `.agents/scripts/public_export.py --help` and the
manifest parser before supplying its current schema. Do not infer a manifest,
remote, allowlist or publication authority from the devkit's own Git origin.
Missing configuration stops export; it must never fall back to publishing HEAD.

The retained `mu_*` role identifiers are stable configuration names, not source
ownership claims or a connection to a private repository. Models, capacities,
languages and workflow methods are configured expertise; they are not evidence
that the present session has those tools, slots, permissions or source inputs.
