---
name: xray-orchestration
description: Start independent Xray Core research and analysis lanes in parallel before detailed main-thread investigation, automatically deliver verified input snapshots, and collect Gas City results. Also coordinate isolated implementation workers and reviewed checkpoints within the human-selected repository policy. Keep a single coupled question local.
---

# Xray orchestration

Use English for every internal assignment, worker message/result, queue comment,
handoff and tool query. The primary coordinator alone translates direct replies
to the human into Russian. Pass concise English task packets without duplicating
Russian history; preserve verbatim evidence and product localization. The native
role and generated external guidance enforce this prompt boundary.

The explicitly selected Windows checkout owns final integration and authorized
publication. Read `docs/PROJECT_SCOPE.md`, `docs/WORKFLOW.md`, the accepted task
and current runtime status for actual inputs, acceptance and blockers. This
toolkit does not connect or configure existing source projects automatically.
Use `.agents/scripts/orchestration.py` for the host runtime entrypoint; verify
status and the target rig/base before dispatch. Installed capacity is 23 workers;
allocate workers to independent questions or disjoint write sets, without a quota.
The current desktop chat may retain its original smaller native agent capacity.
When external admission fails, report the actual failed boundary/runtime check
and distinguish the external pool from native Codex children. WSL2's VM-wide
WSLInterop registration is not a per-distribution enable flag; do not disable it
globally or restart shared WSL to satisfy an existence check. The maintained
launcher checks distribution settings and the current mount inventory.

## Early parallel admission

For capability development, apply `xray-feature-delivery`. Ready candidates can
include native/direct solution research, independent external examples,
consumer-level verification design, disjoint implementation owners, behavior
review and simplicity review. Research selects the approach; it is not a
substitute for implementing and checking all justified requested behavior.
Requirements may change on evidence, with the reason and resulting scope
explicit. Do not close a partial implementation by moving agreed functions to
an unrequested optional future phase. Recompute dependencies after revisions.

Before dispatch, persist a ready-frontier receipt under `.local/` with all
material candidate outputs, owners, prerequisites/input readiness and chosen
native/external lane. Record configured capacity, this chat's observed slots,
actual dispatched IDs/models, and a specific reason for each ready candidate
kept local or deferred. Dispatch all useful ready lanes within actual capacity,
resource leases and write ownership; do not use two, three or four as a ceiling.
Refresh this receipt when scope or prerequisite results change. This is task
decomposition and evidence, not a replacement Gas City scheduler.

Choose native children for bounded same-root analysis and interactive follow-ups;
choose Gas City for durable/isolated work, frozen input delivery or a frontier
larger than the current native capacity. Keep each assignment in one pool. A
small number of ready independent outputs can legitimately use few agents even
in a complex task; retain the dependency/coupling reason in its receipt.

When selecting Gas City for two or more independent advisory questions, read
`references/parallel-batches.md` and run `orchestration.py batch <packet.json>`
after startup and a short task decomposition, before detailed analysis in main.
For the external lane this copies selected worktree files (including dirty docs)
and/or pinned Git blobs into WSL, verifies their hashes in the reader namespace,
creates all native tasks, then routes every job without waiting for earlier jobs.
Use `batch-status <batch_id>` for current native task/session results. Announce
the actual job IDs, models, subjects and progress to the user. Main works on a
different useful responsibility; consume results without redoing whole lanes.

Select as many useful independent lanes as the task supports, up to 23 per batch;
there is no default three-agent ceiling or requirement to fill all slots. Native
city admission remains bounded by its overall 25-session cap. A batch is a ready
frontier, not a dependency scheduler: integrate its results before submitting
dependent work. Implementation work retains the prepared worktree/owned-path
workflow below; this new evidence batch is read-only. Never give WSL agents a
Windows path or assume `/mnt/e` exists. Reuse a batch ID only for the identical
packet and frozen snapshot; after unknown outcomes rerun that same ID, not a
replacement packet. Missing inputs must fail before any work is routed.

Gas City owns the durable queue, mail, sessions and worker worktrees. Use its
pinned pack and native commands, rather than constructing another scheduler.
Implementation workers default to GPT-6.1 Sol high; advisory lanes use the explicit
Luna/Sol/Astra routing below. The parent model stays user-selected. Worker CLI nesting is
disabled: the coordinator dispatches the task graph. Keep one writer per worktree.
Every job identifies its exact base, source/contract inputs, owned paths, expected
result and validation owner. Preserve other workers' changes.

Model routing is automatic. For each job write a scoped JSON packet with `kind`
(`explore`, `implement`, `review`, `deep`), `title`, `body`, and source/evidence
locations, then call `orchestration.py dispatch <packet.json>`. Set `bounded=true`
only for a narrow lookup; cross-owner analysis uses Sol. An unresolved Luna
result moves to Sol. For a Sol technical impasse include `previous_model`,
`blocker="unresolved_technical"`, one `discriminator` and its `evidence`; the
router selects the single Astra adviser automatically. Do not ask the user to
select a model. Preserve results in the Beads handoff, then return ordinary
implementation to Sol. Missing input/access/environment/validation is resolved
directly. The router refuses repeated unchanged Astra escalation.

Prepare the assigned worktree with native `gc worktree ensure` outside the rig's
registered checkout. Run `worker_context.py` there with the exact base, prepared
local queue and native analysis-tools root. The owner prepares ignored host paths
in the rig's independent Git store; worker setup never changes shared exclusions.
Start the worker session in that worktree so its Go MCP opens the same root. If
a stock formula subsequently changes directories, its old MCP root is not valid
for the new worktree: use a fresh scoped session or native gopls in the new root.
The primary supplies shared graph/context evidence once for the pinned base;
workers use live scoped Go evidence for their edits.

Worker commits are local handoff artifacts. Record their source-anchor bead,
worktree, exact commit and changed paths. Do not infer final integration from a
closed bead: the stock pack can finish with a detached commit and no publication.
The integrating owner reviews the actual commits, incorporates accepted paths,
validates the combined bytes, gets independent review and follows
`xray-fork-checkpoint` within the human's explicit task/saved repository policy.
When automatic checkpoints were selected for that exact root/ref, this final
integrated checkpoint is part of completion; do not substitute a report or ask
again for routine permission. Otherwise report the reviewed local state without
inventing commit/push authority. A worker handoff is never integration proof.

Use only the prepared local queue as a worker origin. Keep workflow `push=false`
and `open_pr=false`; workers never publish private source or state to GitHub.
Only the selected integrator can perform an explicitly authorized guarded push. Failed tests,
scope overlap or mismatched base leave the task open with evidence.

Use compiler-aware Go evidence for references/removals. Reuse the MCP session and
index; refresh after relevant changes. Repomix is for narrowly scoped context
bundles. Context7 queries contain only public library names/documentation topics.
Do not send private source or contract text to Context7.
