# Xray workflow and evidence policy

Read [project scope](PROJECT_SCOPE.md) first. Main owns the accepted task, scope,
integration, validation and any authorized publication. Startup reports facts and does not
start an implementation, fetch, build matrix, graph refresh or source export.

## Start and map ownership

For DevKit repository maintenance, use the checks in
[maintenance](MAINTENANCE.md) from the root containing `devkit.py`. The source
startup below requires a separately selected installed Xray checkout. The two
roots have independent files, revisions and acceptance.

Read the source checkout's `AGENTS.md` and any applicable `AGENTS.override.md`,
`.agents/CODEX_PACK.md`, its accepted task/contract and ignored host context. Run
`python .agents/scripts/check_core.py` from that source root after
[workspace setup](CONFIGURATION.md). Report root,
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

## Practical solution research and complete delivery

Use [solution research](../.agents/skills/xray-solution-research/SKILL.md) when a
new or existing capability has an uncertain mechanism or integration. Compare
reachable native behavior, a direct change at its owner, and practical external
implementations. Read actual source and caller examples; public code search is
a discovery aid, not proof that a result fits this checkout or its license.
Run a small deciding experiment when evidence leaves a material question open.
A clear direct change needs no mandatory design document or framework.

Use [feature delivery](../.agents/skills/xray-feature-delivery/SKILL.md) to carry
the justified behavior through its actual input, runtime wiring and consumer.
Research, implementation and review are parts of completing that outcome.
Intermediate slices and spikes do not silently reduce the final scope. Do not
declare completion while agreed behavior remains a stub, is unwired, or has
been renamed optional future work. Resolve authorized integration and tooling
work rather than leaving it as an installation proposal.

Requirements can be revised when evidence shows they are unjustified or conflict
with the goal. Explain material changes and resolve genuinely open human product
or authority choices. Keep a concise account of delivered, revised and blocked
outcomes using the existing task record; a new ledger is not mandatory.

Choose the least machinery that delivers the whole justified result. Wrappers,
validation, retries, fallbacks and extension points need a concrete consumer or
reachable failure. Preserve real errors, cancellation and resource ownership;
missing behavior must not report placeholder success. Apply this to existing
code as well as new work, without a line-count target or speculative defenses.

The solution researcher compares complete alternatives. The behavior reviewer
independently follows the real caller and relevant failures. The simplicity
reviewer challenges unnecessary layers while preserving the required outcome.
Use these roles where their independent work adds value, alongside the existing
correctness, performance and critical reviewers. Tests should detect a meaningful
broken behavior; file presence, mocks and a successful build do not establish
consumer integration. Record only checks actually executed and their scope.

These responsibilities adapt focused ideas from the public projects credited in
[third-party notices](../THIRD_PARTY_NOTICES.md#workflow-responsibility-references).
The DevKit retains its own project authority, models and orchestration.

## Invention, criticism and experiments

Use [design exploration](../.agents/skills/xray-design-exploration/SKILL.md)
when the goal, ownership boundary, technical premise or mechanism is uncertain.
Main starts from the original requested outcome, actual consumer and accepted
authority. The innovator proposes complete alternatives, including existing
native/configuration behavior and small direct changes. An unfamiliar approach
can win on evidence; novelty is not a requirement. Clear direct changes require
neither a design package nor a fixed team.

An independent design critic receives the original task, candidates and evidence.
It supplies a concrete counterexample, stronger complete alternative or supported
acceptance; zero findings is valid. Factual researchers resolve source/API,
version, license and ownership disputes from actual evidence, including claims
made by the critic. Preserve original proposals and criticism alongside revisions
and synthesis. Main selects on observations, not consensus or voting.

The test architect independently designs actual consumer/failure acceptance and
an observation that separates viable alternatives. Through
[decision experiments](../.agents/skills/xray-decision-experiment/SKILL.md), main
assigns the existing Go worker explicit **experimenter mode** with exact scratch
paths, candidate/control, commands, expected observations and resource limits.
The worker actually executes the experiment and returns artifacts, successful
and failed results and limitations. A research plan is not an executed run;
a fixture result does not establish product/device readiness. Main returns
decisive feedback to innovator and critic, revises requirements on evidence with
reasons, resolves genuine human choices and selects implementation.

For competing hypotheses, give independent candidates the original evidence,
confirming/falsifying observations and common meaningful acceptance. Preserve
independent first answers; do not merge incompatible designs by vote. Coupled
state or experiments need one owner or ordered inputs. For algorithm or workflow
improvement, use
[agent evaluation](../.agents/skills/xray-agent-evaluation/SKILL.md): validate
the evaluator against known-invalid and deceptively green cases, compare matched
tasks and held-out variants, retain failures and repeat where variance could
change selection. Measure complete outcomes, missed defects, false findings,
incorrect closure, justified scope revisions and provenance before time/token
costs. Failed selection, unavailable evidence, an unchanged seed or a task
runner's exit zero is not delivered improvement. Polished wording, keywords,
novelty or an LLM grade cannot replace executable correctness evidence.

Continue the selected mechanism through implementation, real-consumer
verification and applicable stable correctness/simplicity/performance/critical
review. Send findings to the authorized writer and recheck affected behavior;
main adjudicates all still-required outcomes before closure. A design report or
experiment does not replace feature delivery. No agreed behavior may be silently
omitted or renamed optional to close a task.

These responsibilities reuse existing native dispatch and Gas City/Beads.
Advisory external packets use `kind=review` and name the competency in their
body; experiment execution uses `kind=implement` with explicit experimenter
mode. Ordinary roles remain Sol 6.1 high, narrow exploration Luna high and one
evidenced unresolved discriminator Astra high. Main's model, capacity 23,
observed limits, no nesting, actual parent permissions and explicit Git authority
remain unchanged. No fixed roster, idea/finding quota, forced novelty, evolution
framework, scheduler or grading service is introduced. See the focused public
[source credits](../THIRD_PARTY_NOTICES.md#invention-and-evaluation-references).

## Runtime and protocol specialists

Use [protocol compatibility](../.agents/skills/xray-protocol-compatibility/SKILL.md)
for the actual changed configuration/protocol/transport seam, not a whole
checkout matrix. `mu_protocol_reviewer` maps decode/Build/Start, DNS/route/handler,
framing/handshake, transport options and named peer implementation/version to the
real caller. Configuration acceptance, local startup, wire exchange and peer
interoperability need separate witnesses, including meaningful successful and
rejecting controls. Packet-sensitive work retains destinations, decoded-byte
boundaries and custody; partial/truncated I/O is tested when implicated.

[Runtime qualification](../.agents/skills/xray-runtime-qualification/SKILL.md)
loads only the reference needed for the assigned boundary:

- Concurrency: `mu_concurrency_reviewer` traces actors/resources through
  admission, transfer, blocking, cancellation, publication, Close, drain and join,
  with lock/wait order, permitted late work and precise completion guarantees.
  Forced interleavings and sensitive controls distinguish races, logical races
  and deadlocks; race-clean alone cannot prove progress. Native shared siblings
  and existing close/join contracts remain intact.
- Security: `mu_security_reviewer` traces reachable attacker input/capability
  through normalization and route/session/trust decisions to a sensitive sink,
  stating prerequisites, exposure, controls, abuse sequence and impact. Routine
  review is distinct from the explicitly requested `security-threat-model` skill;
  no arbitrary hardening limit or vulnerability-name-only finding is required.
- Build/ABI: `mu_build_qualifier` pins source/dependencies, toolchain, target,
  CGO/tags/generated/assembly selections and actual packages/commands. Separate
  download/tool, compile/link, fixture and runtime-load failures. Artifacts need
  hashes/symbols and real consumer API/ABI/load witnesses where implicated;
  library, CLI, cross-build, JNI and device gates do not substitute for each other.
- Performance: existing `mu_performance_reviewer` works in controlled-measurement
  design or independent result-review mode. Pin workload and achieved work,
  payload/reuse, concurrency/warmup, baseline/candidate and variability. Separate
  uninstrumented latency/allocation from CPU/heap/mutex/block/race runs; attribute
  churn, stack growth and retention. Load evidence separates offered/admitted,
  delivered, queued and lost work plus recovery. A broken semantic control
  disqualifies a faster candidate; an underdriven fixture is not capacity proof.

Upstream research provides exact changed API/default/error/build/dependency
facts. Test architect and relevant specialists define native and explicitly
selected extension controls; assigned workers actually execute through the
managed runner and retain failures. Build qualification connects selected target
evidence, protocol review addresses wire seams and behavior review checks the
actual library/config/CLI consumer. Record retained, changed-with-reason,
unsupported and unknown outcomes. A green compilation is not semantic native
compatibility, remote delivery or trust/cancellation proof.

Network-failure experiments name the actual ingress/outbound, fault point and
expected caller-visible error/cleanup, plus surviving siblings where applicable.
Host fault injection does not qualify a live network or device. Actual accepted
Android artifacts use the existing Android validation skill within the selected
source/artifact boundary; downstream app/bridge ownership is not inherited.

Specialists provide distinct evidence; the existing critical reviewer retains
stable cross-boundary integration and release review. Main assigns only useful
ready questions, with no full-roster requirement or automatic OS/build matrix.
Actual execution/repair has one authorized writer; read-only specialists do not
gain publication or tool permissions. External review packets supply specialist
instructions and evidence explicitly and identify the actual pool, rather than
claim a native role ran from its name. No new service or runtime layer is needed.

## Parallel ownership and review

Use the [agent pack](../.agents/CODEX_PACK.md),
[orchestration skill](../.agents/skills/xray-orchestration/SKILL.md) and
[external runtime guide](ORCHESTRATION.md) for early independent lanes,
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

At an authorized checkpoint, stage exact owned paths and the reviewed catalog,
generate the snapshot from the actual index, then stage and verify that snapshot
in the same index before commit. Verify the resulting HEAD afterward. The
[accounting guide](ACCOUNTING_AND_EXPORT.md) gives the ordered commands,
initialization rules and optional shared-runtime evidence map. Recheck if owned
bytes change. The actual commit SHA comes from Git; snapshot history needs no
second commit for its own SHA.

Toolkit maintenance uses its explicit task's validation/accounting policy. A
toolkit-only task must not invent an Xray baseline or runtime module catalog to
make a source accounting gate appear satisfied.

## Validation and fixture races

Use one executor per validation command; reuse matching exact-source receipts.
Rerun after relevant changes, new failures or unresolved concerns. Run host
commands through the [resource guard](ANALYSIS.md#managed-resources-and-limits),
keep durable evidence outside scratch and
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

A filtered source publication is a separately authorized operation using the
user-supplied `.agents/public-export.json`. Follow the
[export guide](ACCOUNTING_AND_EXPORT.md#configure-a-filtered-public-export) for
configuration, network effects and candidate verification, then
[xray-public-ci](../.agents/skills/xray-public-ci/SKILL.md) for checks on that
exact public tree. Preserve all other refs/defaults. DevKit distribution packaging
uses `devkit.py package` under [maintenance](MAINTENANCE.md), independently of
the runtime source exporter.

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
