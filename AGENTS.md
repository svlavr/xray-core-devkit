# Xray Core Devkit contributor instructions

This is an independent public distribution of an Xray-oriented Codex toolkit.
Work on the toolkit only within the human-approved task. This repository does
not select, attach, configure, edit or publish any existing source project by
being present on disk. Integration into a source checkout requires that
project owner's explicit instruction and exact destination.

Read `.agents/CODEX_PACK.md`, `docs/PROJECT_SCOPE.md` and `docs/WORKFLOW.md`.
The human selects the source root, task, behavior contract, adopted upstream
baseline, write set and publication policy. Do not invent product modules,
private contracts, active stages, acceptance or prior authorization. This public
distribution does not include an Xray runtime implementation or its product plans.
For toolkit-only work, the devkit root is the task root; Go/runtime questions
require a separately supplied source checkout. Never treat toolkit startup
success as proof that a source checkout is configured or validated.

Make focused changes; explain what will change and why before editing, then
report what changed. Preserve unrelated dirty work. Verify reachable consumers
before removing an API, function, variable or file. Ask about ambiguous behavior
or authority before dependent edits; continue independent authorized work.

For new or changed capabilities use `xray-feature-delivery` and, when the approach
is uncertain, `xray-solution-research`. Compare current native/configuration,
small direct and applicable external implementations through real source and
deciding experiments. Deliver the whole justified behavior through its actual
consumer. Requirements can be revised on evidence with reasons; resolve material
human choices, and never silently omit agreed work or relabel unfinished behavior
as optional future work. Clear changes need no mandatory architecture package.
See `docs/WORKFLOW.md#practical-solution-research-and-complete-delivery`.

Use `xray-design-exploration` for uncertain goals, premises or mechanisms:
complete alternatives, independent design criticism, factual researchers and
acceptance design feed an actual `xray-decision-experiment` assigned to the
existing worker in experimenter mode. Main returns results to creators/critics,
selects on evidence and continues implementation through consumer verification.
Use `xray-agent-evaluation` for workflow comparisons or disputed completion
claims. No fixed team, idea/finding quota, forced novelty or correctness score
replaces executable evidence. Clear direct changes stay direct. See
`docs/WORKFLOW.md#invention-criticism-and-experiments`.

Main retains the human-selected model and owns integration, validation and Git.
Use one writer per checkout. Assign exact disjoint write sets; independent
writers use isolated worktrees with one integrator. Native children do not
mutate Git or spawn children. An explicitly prepared external worker may make
local handoff commits only in its assigned worktree and local queue; it never
publishes or integrates another worker's changes.

For substantial work with at least two independent evidence lanes, main records
the ready frontier and dispatches useful ready lanes before detailed analysis.
Use native children for bounded same-root work and Gas City/Beads for durable,
isolated, verified-snapshot work or excess native capacity. Keep a coupled
question local with a concrete reason. Record outputs, dependencies, available
slots, ownership and resources; capacity 23 is a bound, not a quota. Launch all
useful ready lanes that fit; explain each kept local or deferred and recompute
when scope or prerequisites change. Do not duplicate jobs across pools.

Roles retain their distributed names: `mu_explorer` uses `gpt-6-luna` high;
`mu_investigator`, `mu_upstream_researcher`, `mu_go_worker`, `mu_reviewer`,
`mu_performance_reviewer`, `mu_critical_reviewer`, `mu_solution_researcher`,
`mu_behavior_reviewer`, `mu_simplicity_reviewer`, `mu_innovator`,
`mu_design_critic`, `mu_test_architect` and `mu_agent_evaluator` use `gpt-6.1-sol` high.
`mu_protocol_reviewer`, `mu_concurrency_reviewer`, `mu_security_reviewer` and
`mu_build_qualifier` also use `gpt-6.1-sol` high.
`mu_deep_reviewer` uses `gpt-6-astra` high for one named technical discriminator
left unresolved after Sol and supplied with its evidence. Missing input,
authority, access or validation is not a model-escalation trigger. Only one Astra
adviser is active. Return ordinary implementation to Sol after its answer.

Read-only and write-set instructions are task constraints. A role's
`sandbox_mode` entry does not enforce a separate sandbox or expand access;
the parent session's effective sandbox and approvals determine tool access.
Keep role instructions within that boundary and report unavailable capabilities.

Use `xray-protocol-compatibility` for an implicated config-to-wire/peer seam and
`xray-runtime-qualification` for selected concurrency, security, build/ABI or
measured-performance modes. Assign the corresponding specialist a distinct
question, with test architect/worker/behavior evidence through the real consumer.
Critical review retains cross-boundary integration duties. No automatic full
roster, build matrix or device/release proof follows. See
`docs/WORKFLOW.md#runtime-and-protocol-specialists`.

Use English for internal analysis summaries, agent tasks/messages, tool queries,
reports, handoffs, queue comments, documentation and commit metadata. Only the
primary coordinator's direct human-chat replies are Russian. Preserve literal
evidence, identifiers and localization. This is a prompt policy, not a claim
about unobservable reasoning.

Keep source/host, cross-build, artifact/binding, device, network, performance and
release evidence separate. Review stable non-trivial changes independently.
Preserve upstream functionality and tests; select tests from a concrete failure
hypothesis and the changed owner. A tool result or passing test grants no new
architecture, deletion or publication authority. Run host tests/builds through
`.agents/scripts/resource_guard.py`; bound time/output and serialize heavy caches.

Keep credentials, host settings, raw logs/captures, attachments, caches, archives
and build outputs out of Git. Host setup generates ignored `.local/` state;
project tools and roles remain editable here. Do not copy private development
documents, project history or product implementation into this public repository.

No automatic source-repository publication is authorized by this distribution.
Commit/push policy comes only from the human's explicit task or saved settings
for the exact repository/ref. Stage exact reviewed owned paths, inspect the
index and use bounded sequential Git with maintenance disabled. No force push,
implicit PR/tag/release, visibility/default change, binary publication, archive
or deletion. Filtered source export additionally requires a user-supplied
`.agents/public-export.json`; never publish a private working history directly.
