# Verified parallel advisory batches

The main coordinator chooses independent questions early. `batch` performs input
delivery and native admission; Gas City performs scheduling, claims and recovery.
Run from the canonical integration root. Before choosing the packet size, record
the task's whole ready frontier in its ignored receipt: candidate/output/owner,
prerequisites and input readiness, lane, observed slot/resource limits and IDs
after admission. Select every useful ready external advisory lane that fits
capacity; name the exact reason for any ready candidate handled locally or
deferred. Reassess after prerequisite completion and user steering. Batch size
comes from this inventory, never a default two/four-agent policy. Native bounded
work may use the same inventory without creating duplicate external jobs. Actual
overlapping execution requires task start/end evidence, separately from the
number of queued or total lifetime jobs. Example packet saved under `.local/`
for a source checkout that actually contains the listed stock files (adjust and
verify every path/ref against the supplied task before dispatch):

```json
{
  "batch_id": "transport-ownership-analysis",
  "sources": {
    "scope": {
      "ref": "WORKTREE",
      "paths": ["docs/PROJECT_SCOPE.md", "docs/WORKFLOW.md"]
    },
    "dns": {"ref": "HEAD", "paths": ["app/dns/dns.go"]},
    "transport": {"ref": "HEAD", "paths": ["transport/internet/hysteria/dialer.go"]}
  },
  "jobs": [
    {"key": "dns", "kind": "review", "title": "DNS lifetime overlap",
     "inputs": ["scope", "dns"],
     "body": "Map the current DNS cancellation and retirement owners against the supplied plan. Return precise gaps, source locations and unknowns; do not perform the transport lane."},
    {"key": "transport", "kind": "explore", "bounded": true,
     "title": "Hysteria cancellation inventory", "inputs": ["transport"],
     "body": "Identify the dial cancellation checks and cleanup owner in the supplied file. Return exact symbols and source lines; no broader architecture review."}
  ]
}
```

```powershell
python .agents/scripts/orchestration.py batch .local/my-batch.json
python .agents/scripts/orchestration.py batch-status transport-ownership-analysis
```

Use a new descriptive batch ID for new work/evidence. Source aliases map to
verified Linux directories injected into each task. `ref` accepts WORKTREE,
HEAD, or a full immutable commit SHA already available locally. Explicitly list
regular files; no directories, glob expansion, path traversal, links, credentials,
Git storage or generated host settings. Selected `.local` evidence files may be
included explicitly; never include credentials, captures or unrelated raw logs.
Limit each batch to 512 files / 8 MiB per file / 64 MiB total. Worktree contents
are frozen by per-file SHA256; HEAD alone does not describe dirty documents.

Each job selects source aliases, has one concrete question and expected output,
and uses existing model routing. Use `kind=explore,bounded=true` only for a narrow
lookup; cross-owner analysis and reviews use Sol 6.1 High. The existing evidence
gate and single pool still restrict Astra. No nested delegation or source writes.

Set `role` to the selected maintained competency, for example
`"role": "mu_concurrency_reviewer"`; model pools do not identify the role.
Optional `skills` selects extra installed skill packages. Before task creation,
profile instructions/model/effort and helper/skill/public-document hashes are
frozen into per-job tooling and bound in native metadata. Advisory cwd is that
frozen tooling root; assigned source aliases remain explicit separate inputs.
Mutable launch receipts/scratch live in a Linux-user-owned run directory outside
the immutable snapshot. Source HEAD and captured WORKTREE/tooling hashes remain
distinct. Quoted/dotted overrides cannot replace competency/root bindings.
Resumes keep pinned helpers; preserve old jobs/bundles and uncollected comments.
These advisory tasks use city Beads storage, while separate prepared
implementation dispatch uses `rig:mu-core` and `mux-` IDs.

The adapter stores a durable local receipt before native task creation. Stable
IDs and content hashes prevent accidental duplication: rerun the identical packet
after inspecting an interruption. It reconciles existing native tasks and routes;
it does not overwrite another assignment or restart closed tasks. Open unassigned
tasks already marked for the same pool receive one native idempotent `--nudge`
on replay: a route marker alone does not prove controller wake-up. Actual claim
and completion remain separate evidence. A partial
submission is reported explicitly; do not count it as all jobs completed.

Report job IDs/models immediately, then use bounded status checks while doing
independent work. A closed task without a DONE result is not acceptance. Read the
actual comments and preserve NEEDS_CONTEXT/unresolved outcomes. Per-task start
and close times and distinct session identities are evidence of execution;
configured capacity or a list of queued tasks is not proof of simultaneous work.
DONE means an advisory answer was completed, including findings and limits; it
does not mean that implementation was accepted. Main resolves findings before
final integration and any reviewed checkpoint explicitly selected by the human.

Configure validates the four exact reviewed Gas City hook fingerprints through
Codex's native API. Each frozen launch then binds only its exact cwd and those
existing hook identities through invocation-scoped project/hook overrides. Extra or changed
hooks fail for review; there is no blanket hook-trust bypass. This prevents new
workers from remaining at an unseen confirmation prompt. Context windows and
the total-scope compaction threshold apply per conversation, not across models
or across concurrent agents.
