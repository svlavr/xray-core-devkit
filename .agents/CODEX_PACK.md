# Xray Core Devkit agent pack

## Working language

Use English for internal analysis/reasoning summaries, agent tasks/messages,
tool/MCP query text, reports, handoffs, queue comments, docs and commit metadata.
Only the primary coordinator's direct commentary/questions/final replies to the
human are Russian. A worker's coordinator is an internal recipient, even when
its output appears in the app. Give native children concise English packets;
translate the human requirement once rather than copying Russian chat history.
Preserve exact quotes, source data, paths, identifiers and product localization.
This is a prompt policy, not proof of the language of unobservable reasoning.

## Authority and routing

Main retains the user-selected parent model and effort, owns the accepted task,
coupled edits, integration, Git and validation. Host values come from
`.local/workspace/context.json`; the human supplies source root, contract, adopted
baseline and authority under `docs/PROJECT_SCOPE.md`. `docs/WORKFLOW.md` owns the
public evidence/accounting process. This independent toolkit neither selects nor
connects an existing source project. Startup reports facts; it never fetches,
copies runtime, refreshes indexes, starts implementation or grants publication.

For toolkit-only maintenance, the root containing `devkit.py` is the task root.
Use `devkit.py verify`, `audit.py` and `workspace.py validate` there to inspect
the distribution and skill/role inventory. `workspace.py setup` and
`check_core.py` require an installed Xray source checkout; their results are
source-root startup evidence and are not DevKit-root checks.

Use one task for a small/coupled lookup. For a substantial task with two or more
independent evidence lanes, dispatch them BEFORE detailed local investigation;
do not perform each lane yourself and delegate only the last review. After the
startup guard, identify independent questions and expected artifacts, then use
native children or, for the selected external lane, `orchestration.py batch
<packet.json>` for verified inputs and native Gas City admission. Main advances
integration/another independent owner while they run.
For upstream adaptation, examples include release/PR evidence, DNS resolver
lifetime and transport/TLS compatibility. Choose lanes from the actual task, not
a fixed roster. Before admission, save the current ready frontier in an ignored
task receipt: each candidate's owner, concrete output, dependencies/input state,
execution lane and returned ID. Record observed available slots separately from
configured capacity. Dispatch every useful ready lane within those slots and
resource/ownership limits before waiting; every ready lane left with main or
deferred needs a concrete coupling, missing-input, resource or ownership reason.
Two/four workers are not a default ceiling. Recompute the frontier after new user
scope, a prerequisite result or integration, including before final review.
If work is genuinely coupled, state that reason and stay local.
Fresh native sessions configure capacity 23; a running
chat can retain a smaller host limit. Use `xray-orchestration` to choose the lane.
Native children suit bounded same-root questions and interactive follow-ups.
Gas City/Beads suits durable work, isolated worker roots, verified snapshot
delivery and excess native capacity. Do not duplicate assignments across pools.
One writer per checkout, with disjoint
worker worktrees and one integrating owner. Only the coordinator dispatches.
Native children do not change Git. External workers may create local commits in
their assigned worktrees; only main integrates and publishes explicitly authorized checkpoints.
External advisory batches are the default when native slots are too few; they do
not require a new desktop chat. Tell the user which lanes were dispatched, the
actual IDs/models and results. External jobs appear as wrapper commands, not
native child cards. Report observed overlap separately from configured capacity.

Roles: `mu_explorer` (Luna high); `mu_investigator`,
`mu_upstream_researcher`, `mu_go_worker`, `mu_reviewer`,
`mu_performance_reviewer`, `mu_critical_reviewer` (Sol 6.1 high);
`mu_solution_researcher`, `mu_behavior_reviewer` and
`mu_simplicity_reviewer` also use Sol 6.1 high;
`mu_innovator`, `mu_design_critic`, `mu_test_architect` and
`mu_agent_evaluator` use Sol 6.1 high;
`mu_protocol_reviewer`, `mu_concurrency_reviewer`, `mu_security_reviewer` and
`mu_build_qualifier` also use Sol 6.1 high;
`mu_deep_reviewer` (Astra high, one named unresolved discriminator after Sol).
The distributed model policy is: `gpt-6-luna` high for narrow
exploration, `gpt-6.1-sol` high for ordinary roles and external worker defaults,
and `gpt-6-astra` high only for one named deep discriminator. Preserve the
user-selected parent model. Model/effort must be explicit; never inherit Astra
into the worker pool. Fresh discovery is required for changed native roles.
Select the role/model automatically without asking the user. Generic child calls
must use the routed model explicitly with scoped context, rather than inheriting
the parent through an unrestricted full-history fork. Use the single Gas City
`mu-deep` pool for automatic Astra escalation; a native deep reviewer is a fallback
only when that runtime is unavailable and no other Astra adviser is active.
`orchestration.py dispatch <task.json>` applies `orchestration/models.json`: Luna
High for bounded lookup, Sol 6.1 High for broader analysis/implementation/review,
then one Astra High adviser for a named discriminator still unresolved after Sol.
Missing inputs/access/environment/test results require evidence, not escalation.
After the adviser resolves a question, return implementation to Sol 6.1 High.

Main selects competencies from the actual nineteen maintained profile descriptions,
then passes `role` to the execution route. Use `session.py --list-roles` for the
catalog; it also works in the standalone DevKit without source setup. Preserved
source-owned extra roles/skills remain owner-managed and do not enter this
catalog or generated mappings automatically. Native `agent_type` admission and
CLI profile execution are distinct evidence. When an existing session cannot
admit a named native type, use the installed `session.py --role <name> --exec ...`
or an external packet with `role`, within the same accepted task. No new chat
or repeated routine authorization is required. Role execution applies the actual
TOML instructions, model and high effort; the no-role launcher retains normal
parent settings. It never enables permissions or tools beyond inherited access.
External model pools are execution targets, not specialist identities. Frozen
launches bind the selected profile, helpers, skills and public authority docs
before a model enters. Preserve active jobs, old bundles and uncollected results.

Use a narrow explorer for one independent path; an investigator for a bounded
cross-owner question; upstream researcher for material external evidence;
worker for an accepted disjoint write set. Stable non-trivial diffs receive
independent review: ordinary reviewer for correctness/process, performance
reviewer for hot-path claims, critical reviewer for substantial concurrency,
security, shared runtime, Android or release boundaries.

## Complete engineering outcomes

For new capabilities and changes to existing behavior use
`xray-feature-delivery`; use `xray-solution-research` when the approach needs
evidence. The solution researcher compares native/direct/external approaches;
behavior and simplicity reviewers independently check actual consumer wiring
and unnecessary machinery. Main can run independent research, validation design,
disjoint implementation owners and applicable reviews concurrently. Select the
ready work from dependencies, not a fixed small team or a 23-worker quota.

Requirements can be mistaken or revised on evidence. Explain the deciding facts
and update the actual task scope; escalate material unresolved human choices.
Do not silently omit agreed behavior, finish only infrastructure, or reclassify
unfinished functions as optional future work to close the task. Intermediate
slices are execution steps toward the full justified outcome, not permission
to stop early. Choose simple complete implementations, with safeguards justified
by real behavior rather than speculative wrappers or placeholder success.
Clear direct changes need no mandatory architecture package. The public process
and adaptation boundary are in
`docs/WORKFLOW.md#practical-solution-research-and-complete-delivery`.

Use `xray-design-exploration` when goals, premises or mechanisms are uncertain.
An innovator offers complete alternatives; an independent design critic gets
the original objective and challenges assumptions or supports acceptance.
Factual researchers resolve disputed source/API/version/license claims.
`mu_test_architect` designs consumer acceptance and the deciding observation;
`xray-decision-experiment` assigns the existing worker explicit experimenter
mode and owned scratch for an actual run. Main returns observations to the
creator/critic, adjudicates and continues implementation/consumer verification.
For competing hypotheses use common meaningful tests; algorithm/workflow
comparison uses `mu_agent_evaluator` under `xray-agent-evaluation`, including
known-invalid evaluator checks. No forced novelty, fixed team/round count,
idea/finding quota, votes or keyword/LLM score establishes correctness.
Clear direct changes need no added ceremony. The public authority is
`docs/WORKFLOW.md#invention-criticism-and-experiments`.

For changed config/protocol/transport/peer semantics use
`xray-protocol-compatibility` and `mu_protocol_reviewer`. Select only implicated
`xray-runtime-qualification` references: `mu_concurrency_reviewer` for resource
transitions/wait graphs; `mu_security_reviewer` for reachable trust-to-sink
paths; `mu_build_qualifier` for target/ABI/native-consumer witnesses; existing
`mu_performance_reviewer` for controlled measurement design or independent
results review. Test architect and owned workers supply sensitive actual checks;
behavior review follows the real caller. Critical review retains genuine
interactions and release boundaries. No default full roster or platform matrix,
universal joins/quotas, device acceptance or new runtime owner. External review
packets explicitly include the specialist competency/instructions and inputs;
their pool identity is not proof that a named native role ran. See
`docs/WORKFLOW.md#runtime-and-protocol-specialists`.

## Dispatch and review

Give objective/role, exact checkout/refs, read set, write set or none, dirty
exclusions, model/effort, known facts, observable acceptance, validation executor
and stop conditions. Tell writers they are not alone and to preserve other work.
Use minimal context, never a generic explorer-writer-reviewer sequence.

Return DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT or BLOCKED with exact paths,
evidence, unknowns and next action. Findings require a trigger, consequence and
location. Do not infer architecture/permission from tool output or passing tests.
External advisory batches instead use the exact first-line result envelope in
their task: `status: DONE`, `status: NEEDS_CONTEXT`, or
`status: UNRESOLVED_TECHNICAL`. DONE means the scoped answer is complete, including
any findings/limits; it does not mean the parent change passed review. Main must
read and resolve the findings before accepting or checkpointing implementation.
Missing authority/artifact/consumer/workload evidence cannot be solved by a
stronger model. Escalate Sol to Astra only for one evidenced unresolved technical
question; never repeat an unchanged assignment or use Astra as default worker.

Main reviews current integrated bytes, deduplicates findings and repairs causes.
Review only stable files. Assign each validation command to one executor; reuse
matching receipts and rerun after relevant changes, failures or unresolved risks.
Serialize cache-heavy work. Source tests, cross-builds, artifact/device, network,
performance and release remain separate. Do not weaken original tests.

## Evidence freshness

Every checkpoint and implementation report follows `docs/WORKFLOW.md`. One local
Git counter and the user-reviewed `.agents/metrics/modules.json` owner catalog
provide actual source module/shared totals and per-file lengths. The human
supplies the catalog/baseline; no private product owners are inherited. Record runtime files
and full lengths separately from the fork added/deleted/net delta; retain tests,
generated code, test support, docs and tools as distinct categories. Capture
before, count/verify the exact owned INDEX including the snapshot, then verify
HEAD after an authorized commit. Report unchanged runtime explicitly for process
work, baseline/catalog moves explicitly, and concrete reasons for growth.
Unknown new fork runtime owners or stale snapshots require correction before
checkpoint. Count shared integration once; no quotas, automatic deletion, network
service or second metadata commit. Publication guards follow the selected repository policy, not an inherited remote.

Remote ref observations must distinguish LIVE, REUSED and UNAVAILABLE. Use
`remote_evidence.py` for a bounded fresh query with URL, exact ref and observation
time. Never substitute local HEAD, a pinned SHA or a previous response after a
failed query and label it freshly verified. Reused evidence keeps its original
observation time and points to its source; the current failure remains recorded.
Receipt creation time is not the observation time. Preserve historical receipts
and attach a correction/addendum rather than rewriting them as current evidence.
Configured/enabled MCP, successful invocation and confirmed results are likewise
different claims. Record the tool/root/profile actually used; invoke only tools
needed for the question, without manufacturing activity for unused servers.

For questioned compaction, use `context_diagnostics.py --thread <exact-id>` to
compare the actual runtime scope/limit/model with the server last-request usage.
The UI request counter and full active-context accounting are different; neither
an apparent UI percentage nor a generated config alone proves a bad trigger.
Inspect the exact event before changing policy. Missing/retained-log evidence is
UNKNOWN; changing the threshold or scope must not manufacture a UI percentage
guarantee. The user-selected primary model remains unchanged.

## Analysis and host setup

Use `xray-code-analysis` for shared Go/reference/removal questions, choosing only
needed semantic/AST/reachability evidence. Checkout-bound launchers use the
installed host context and separate source/profile caches. Confirm actual
`go_workspace` before MCP queries; an identity report alone is not that proof.
Graphs are supplementary, refreshed on demand for committed source; dirty source
uses live evidence. Reuse persistent backends and unchanged indexes. Source
fingerprints, rather than documentation-only HEAD changes, govern freshness.
No automatic platform matrix or synthetic success.

## Temporary resource lifetime

Run host test/build/validation commands through
`python .agents/scripts/resource_guard.py --timeout <seconds> -- <command>`.
For example, `python .agents/scripts/resource_guard.py -- go test ./common/buf`.
The managed command owns its descendant tree and an isolated ignored
`.local/host/transient/run-*` TEMP/TMP/GOTMPDIR. Normal exit, failure, timeout
and owner death terminate only that tree; inactive marked scratch is recovered
on the next managed invocation. `--clean` recovers only inactive owned runs.
Keep outputs and evidence outside scratch; shared GOCACHE/GOMODCACHE stay intact.
Do not use broad process-name kills, purge shared caches, or delete unmarked
global TEMP folders. A blocked/locked/reparse scratch run is retained safely.
MCP frontends evict heavy backends after 120 idle seconds and recreate/replay
initialization on demand. Running requests are not idle; their deadlines remain
separate. Fresh processes are required to adopt edited launchers/configuration;
do not restart another active chat globally. Session launchers also own child
TEMP and lifetime; direct desktop validation still uses the managed runner.

Windows gopls, GitNexus, sandboxed Repomix, Context7 and grep.app are enabled for fresh
primary sessions. Android remains opt-in. No index is built merely at startup.
Repomix can read the selected checkout and owner-approved contracts; its sandbox
restricts paths to that root, not to files cleared for public disclosure. Request narrow include patterns and
exclude `.local` raw evidence from bundles. Context7 receives public documentation
queries, and grep.app receives public code-example queries through `searchGitHub`;
neither receives private source, contracts, credentials or logs. Inspect actual
source, its revision and license before reuse. Worker profiles include these
remote discovery services and bind semantic tools to their own source
root; do not multiply primary-root services across isolated workers.
Worker-only `exa_public_research` additionally provides allowlisted public
`web_search_exa`/`web_fetch_exa` over HTTPS; search requires query and objective,
fetch takes urls. Never submit private questions or inputs. Its approval intent
does not broaden actual parent permissions; primary MCP configuration is unchanged.
Never treat missing tools/package loads as an empty reference inventory.

Project tools are edited in place. `.agents/` and `.codex/agents/` are tracked
in this independent public distribution. Integrating them into a source checkout
requires the human's explicit destination/task; never attach existing projects
automatically. `workspace.py setup` generates ignored host settings without
copying source or project files. `verify` checks the selected root, configured
expected-branch/publication policy and role/config agreement. It does not require
an old installer or another checkout. Use the project-local session launcher
for fresh role discovery when ignored config is not auto-loaded.

Role `sandbox_mode` entries describe intent; they do not impose a separate
enforcement boundary or broaden access. Parent-session sandbox and approval
settings determine actual access. Read-only and exact owned-path instructions
remain mandatory; never treat a role field as permission to write or publish.

Successful implementation ends with integrated validation and independent review,
then `xray-fork-checkpoint` applies only the human's explicit task/saved policy.
Automatic reviewed local commit/push is supported when selected for the exact
repository/ref; this distribution grants neither by default. A closed task or
worker's detached commit does not replace an authorized integrated checkpoint.
Filtered public builds/tests use only verified public source. Export additionally
requires user-supplied `.agents/public-export.json` and explicit destination;
private working commits/history must never be pushed directly to a public export
remote. No source export/CI is triggered merely by toolkit maintenance.
