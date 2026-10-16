---
name: xray-fork-checkpoint
description: Checkpoint a completed verified and independently reviewed owned Xray slice within the human's explicit repository policy. Commit or non-force push only when authorized for the exact root and ref; never publish private working history through a source export.
---

# Reviewed checkpoint

Derive checkpoint authority from the human's current task or explicit saved
settings for the selected repository. This distribution grants no default
commit/push authorization and supplies no private remote or branch. A configured
remote alone is not publication authority. If the owner selected automatic
checkpoints, perform them at successful completion without asking again for
routine permission; otherwise preserve the reviewed result and report its exact
local state. Complete all authorized review/validation before seeking any
additional, actually required Git permission.

Require the actual integrated bytes, independent review and relevant validation.
A worker commit, closed Beads item or session-stop event alone is not acceptance.
Main alone owns integration and Git publication. External worker commits remain
local handoff artifacts in their prepared worktrees/queue. Read the accepted task,
`docs/PROJECT_SCOPE.md`, `docs/WORKFLOW.md` and run project startup. Check exact
root, branch, configured expected-branch policy, remote URL and authorized ref.

Check no unrelated staged/dirty overlap, stage an exact owned-path allowlist,
inspect content/whitespace and follow only the authorized local/remote policy.
Use the reviewed `.agents/metrics/modules.json`; count the exact owned staged
view with `python .agents/scripts/source_size.py snapshot --source INDEX --upstream <adopted-official-SHA>
--output .agents/metrics/source-size.json`, add that snapshot to the owned set,
and run `python .agents/scripts/source_size.py verify --source INDEX` before commit. Run
`python .agents/scripts/source_size.py verify --source HEAD` after commit, before any publication.
Missing baseline/catalog/accounting is an explicit unresolved gate, not a
fabricated verified footprint. Capture before/after files, per-file lengths,
module/shared totals, added/deleted/net and growth reasons; separate categories.
Docs/tools-only work reports runtime unchanged only when observed. The commit
SHA comes from Git; no second metadata commit or GitHub API for its own SHA.

Keep Git hidden, sequential, bounded, with maintenance disabled. If an exact
non-force push is authorized, verify that remote ref afterward. Use
`python .agents/scripts/remote_evidence.py --remote <authorized-remote> --ref <full-authorized-ref>
--expected <full-HEAD> --output .local/<new-receipt>.json` for saved proof.
An unavailable/mismatching response is not PUBLISHED verification: retain the
commit and failure, reconcile the exact remote ref, then report actual state.

Track only the selected project's intended source, instructions, roles and
reviewed documents. Exclude credentials, host config, raw providers/logs/captures,
attachments, caches, archives and binaries. No force-push, implicit PR, release,
tag, visibility/default change, binary upload, archive, retirement or deletion.
Report exact SHA and `PUBLISHED`/`LOCAL_ONLY`/`NO_CHECKPOINT` with the reason.

Filtered public source publication is separate, requires explicit destination
and `.agents/public-export.json`, and follows `xray-public-ci`. Never push a
private working HEAD/history to a public export destination. Process-only
checkpoints do not automatically launch source CI or Go/platform matrices.
