# Xray workflow and evidence policy

Read `PROJECT_SCOPE.md` first. Main owns the accepted task, scope, integration,
validation and any authorized publication. Startup reports facts and does not
start an implementation, fetch, build matrix, graph refresh or source export.

## Start and map ownership

Read the source checkout's `AGENTS.md` and any applicable `AGENTS.override.md`,
`.agents/CODEX_PACK.md`, its accepted task/contract and ignored host context. Run
`python .agents/scripts/check_core.py` from the configured root. Report root,
branch/HEAD, adopted official baseline, remotes, publication restrictions and
dirty paths. Toolkit-only setup does not establish source/runtime readiness.

An external worker verifies its owner-generated `.local/workspace/worker.json`,
root, exact base, local queue and actual Go workspace. It does not apply an
integrator's publication authority. Tools and roles are edited in place; host
setup generates ignored configuration rather than maintaining a second tool copy.

Before runtime changes, identify current reachable owners, consumers, state,
locks, interfaces, dependencies and failure/cancellation paths. Compare native
reuse, the smallest change at that owner and evidence-only outcomes. Apply
`xray-code-analysis` for shared/exported Go, responsibility moves or removal.
Preserve native errors, packet destinations, byte boundaries, batching, resource
custody and explicit partial/unknown outcomes. Product policy stays with its
actual external owner unless the accepted contract explicitly selects it here.

## Parallel ownership and review

Use `.agents/CODEX_PACK.md` and `xray-orchestration` for early independent lanes,
ready-frontier receipts, explicit role/model routing and bounded resources.
Packets include objective, exact root/refs, read/write sets, exclusions, known
facts, acceptance, executor and stop conditions. Preserve all other edits.
One writer owns each checkout; isolated workers return local owned-path commits
for main to inspect and integrate. Only the coordinator dispatches.

Review stable integrated bytes independently. Use the ordinary reviewer for
correctness/regressions, performance reviewer for hot-path claims and critical
reviewer for substantial shared runtime, concurrency, security, Android or
release boundaries. Findings need a realistic trigger, consequence and exact
source location. Main resolves findings before accepting the slice. A DONE
advisory result means its answer is complete, not that implementation is approved.

## Source-size accounting

Use the local offline counter `.agents/scripts/source_size.py` and the reviewed
owner catalog `.agents/metrics/modules.json`. The owner supplies actual groups,
path rules and shared integration ownership; no private product catalog is
bundled. Missing catalog/baseline or an uninitialized snapshot is explicit and
blocks a claim of verified source accounting, without inventing module totals.

Count committed source at startup. Record files and per-file lengths, plus fork
added/deleted/net lines against the exact adopted official upstream SHA. Separate
runtime, tests, generated code, test support, docs and tools; shared integration
is counted once. Explain growth and baseline/catalog changes. For process-only
work, report runtime unchanged only after observing it. Line counts grant no
removal authority, target ranges or quotas.

At an authorized checkpoint, stage exact owned paths, generate the snapshot
from the actual index and add it to that same owned set:

```powershell
python .agents/scripts/source_size.py snapshot --source INDEX --upstream <adopted-official-SHA> --output .agents/metrics/source-size.json
python .agents/scripts/source_size.py verify --source INDEX
```

Inspect and verify the exact index including its catalog/snapshot before commit.
After committing, run `python .agents/scripts/source_size.py verify --source HEAD`. The actual commit
SHA comes from Git; snapshot history lives in Git and requires no second commit
for its own SHA. Recheck if owned bytes change. Toolkit-only projects must use an
appropriate explicit catalog/baseline; do not label missing runtime metrics as
an Xray source verification.

## Validation and fixture races

Use one executor per validation command; reuse matching exact-source receipts.
Rerun after relevant changes, new failures or unresolved concerns. Run host
commands through `resource_guard.py`, keep durable evidence outside scratch and
serialize cache-heavy work. Select focused tests from affected behavior; race
shared state, and measure before/after for quantitative performance claims.
Do not weaken original tests or apply exceptions from another project.

Record every actual failing job and attempt. A fixture-race disposition requires
the concrete conflicting access pair, owning source blobs/build configuration,
reproduction and evidence from the selected stock baseline. A historical
upstream fixture failure does not excuse a new/fork race or corrected source.
Any accepted exception must be explicitly supplied by this project's owner;
retain FAIL counts and state its exact boundary. Retry only a demonstrated
transient failure on the same SHA, preserving original attempts. Missing,
running, skipped or cancelled checks are not PASS.

Keep source/host tests, cross-build, artifact/binding, AVD/physical device,
network, performance and release results separate. Android validation requires
an actual accepted executable artifact or explicit artifact-validation task,
exact source/build/artifact hashes, toolchain/API/ABI, caller, device/workload,
native loading, lifecycle, cancellation, socket protection/underlay ownership
and resource cleanup evidence. Host success proves none of those implicitly.

## Checkpoints and publication

Use `xray-fork-checkpoint` only within the explicit task/saved repository policy.
No commit or push authority is inherited from this public distribution. If the
human has authorized automatic checkpoints for the exact root/ref, complete
review and validation, then perform that policy without repeatedly requesting
routine permission. Otherwise deliver the reviewed result and precise local
state; ask only when an additional Git action is required and unapproved.

Only main stages/integrates/publishes. Inspect exact owned index bytes and dirty
overlap. Use hidden bounded sequential Git with maintenance disabled; non-force
push to the explicit authorized remote/ref only. Verify the observed remote SHA
with `.agents/scripts/remote_evidence.py`; unavailable or mismatching proof is
not PUBLISHED. Report `PUBLISHED`, `LOCAL_ONLY` or `NO_CHECKPOINT` with reason.

A filtered source publication is a separately authorized operation through
`.agents/scripts/public_export.py` with the user-supplied
`.agents/public-export.json`. Prove the committed allowlist/blob correspondence,
public-only or official ancestry and exact public SHA before publication. Do
not mirror a private working branch, push its history or include credentials,
host state, private instructions/documents or raw logs. Public CI runs on the
filtered public tree without private access. Preserve all other refs/defaults.

No implicit PR, tag, release, binary upload, visibility/default change, archive,
retirement or deletion follows from a checkpoint or CI run. Toolkit maintenance
does not automatically trigger a source export or Go/platform CI matrix.

## Freshness and resource lifetime

Remote observations are `LIVE`, `REUSED` or `UNAVAILABLE`, with URL, exact ref,
observation time and original receipt. A failed live query must not be replaced
by a cached/local SHA presented as fresh. Correct historical receipts by addendum.
Configured MCP, invoked MCP and confirmed evidence are distinct claims.

Graph caches are supplementary and source-fingerprint scoped; dirty source
requires live semantic/AST evidence. Check actual tool root/profile/build tags.
On-demand committed-source refresh does not authorize a startup indexing matrix.
External documentation services receive public queries, never private source or
contract text. Missing tools do not imply zero references.

Managed commands own only their descendant tree and marked isolated scratch.
Recover only inactive owned runs; preserve locked/reparse/unmarked paths, shared
Go caches and other sessions. MCP heavy backends evict after 120 idle seconds
and replay initialization on demand; active requests have separate deadlines.
Fresh processes adopt edited launchers/configuration. Never globally restart
WSL or another chat, kill by broad process name or purge global TEMP/caches.
