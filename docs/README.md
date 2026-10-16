# Documentation

Xray Core DevKit supplies Codex skills, specialized roles and the supporting
analysis, process, accounting and orchestration tools. It contains no Xray
runtime. Start with the [repository overview](../README.md), then use the guides
below for the workflow you need.

## Choose the correct root

The **DevKit root** is the downloaded or cloned distribution containing
`devkit.py`. Run installation, update, distribution verification and packaging
there. The **source root** is the explicitly selected Xray checkout receiving
the toolkit. Run workspace setup, Codex sessions, Go analysis and source work
there. The source module must remain `github.com/xtls/xray-core`.

Installation copies ordinary local files. The installed source checkout does
not depend on the DevKit checkout remaining available. Installing the toolkit
does not select a source task, attach another project or grant publication
authority. Supply the actual root, task, contract, baseline, write set and Git
policy using [project scope](PROJECT_SCOPE.md).

## Install, update and start

Follow [installation](INSTALLATION.md) for requirements, locked dependency
provisioning, conflict handling and the external runtime prerequisites. These
commands are a short route through that guide; paths are illustrative.

From the DevKit root:

```powershell
python devkit.py verify
python audit.py
python devkit.py install --target D:/Work/Xray-core --dry-run
python devkit.py install --target D:/Work/Xray-core
```

From the installed source root:

```powershell
python .agents/scripts/dependencies.py install --tools D:/Tools/xray-analysis
python .agents/scripts/workspace.py setup --analysis-tools D:/Tools/xray-analysis
python .agents/scripts/workspace.py verify
python .agents/scripts/check_core.py
python .agents/scripts/session.py --
```

Use `dependencies.py status --tools D:/Tools/xray-analysis` to inspect and reuse
an existing matching tool installation. Supply your own Codex authentication.
An adopted official upstream baseline requires an explicit reviewed revision;
setup's default local HEAD is only a comparison selection.

To update, obtain a newer reviewed DevKit copy and run from that DevKit root:

```powershell
python devkit.py update --target D:/Work/Xray-core --dry-run
python devkit.py update --target D:/Work/Xray-core
```

The installer checks recorded hashes and preserves conflicting local edits for
explicit reconciliation. Rerun workspace setup after an accepted update and
start a fresh session when settings, role definitions or launchers changed.
See [configuration](CONFIGURATION.md) for existing-config handling and every
generated setting.

## Guide navigation

- [Project scope and authority](PROJECT_SCOPE.md): the inputs a source owner
  supplies, permitted work modes, contracts and publication boundaries.
- [Workflow and evidence](WORKFLOW.md): startup, reachable ownership, independent
  review, focused validation, source accounting and checkpoint rules.
- [Installation](INSTALLATION.md): distribution installation/update, analysis
  dependencies, fresh sessions and prerequisites.
- [Configuration](CONFIGURATION.md): baseline/branch guards, optional project
  policy, models, context settings, MCP profiles and ignored host state.
- [Go and source analysis](ANALYSIS.md): semantic references, package consumers,
  syntax, reachability, graph freshness and guarded command lifetime.
- [Accounting and source export](ACCOUNTING_AND_EXPORT.md): reviewed owner
  catalogs, exact Git blob measurements, export manifests and ancestry checks.
- [External orchestration](ORCHESTRATION.md): the complete Gas City/Beads/Dolt
  runtime, selected WSL environment, verified input batches, worker provisioning,
  result collection and integration.
- [Maintenance](MAINTENANCE.md): toolkit regressions, public content review,
  manifest verification and distribution packaging.
- [Third-party notices](../THIRD_PARTY_NOTICES.md): dependency provenance and
  license terms; the toolkit's own [license](../LICENSE) does not replace them.

The [agent pack](../.agents/CODEX_PACK.md) is the coordinating instruction set.
It connects the human's accepted scope to the skills, worker routing and
evidence policy. The [contributor instructions](../AGENTS.md) apply to toolkit
maintenance.

## The eleven skills

Each link opens the actual maintained skill entrypoint, including its linked
references and commands.

- [xray-core-start](../.agents/skills/xray-core-start/SKILL.md): report the
  selected root, branch/HEAD, baseline, remotes, policy and dirty paths. Startup
  reports facts without starting implementation, indexing or publication.
- [xray-fork-research](../.agents/skills/xray-fork-research/SKILL.md): investigate
  upstream behavior, dependencies, licensing and source evidence before deciding
  whether a change is needed.
- [xray-code-analysis](../.agents/skills/xray-code-analysis/SKILL.md): trace Go
  ownership, references, import impact and named removal questions with the
  applicable source/build profile.
- [xray-fork-implement](../.agents/skills/xray-fork-implement/SKILL.md): implement
  an accepted bounded slice, validate and independently review the integrated
  result, then apply the owner's explicit checkpoint policy.
- [xray-orchestration](../.agents/skills/xray-orchestration/SKILL.md): dispatch
  useful independent lanes early, deliver verified external inputs and coordinate
  isolated worker results. Its [parallel batch reference](../.agents/skills/xray-orchestration/references/parallel-batches.md)
  gives the advisory batch contract.
- [adversarial-reviewer](../.agents/skills/adversarial-reviewer/SKILL.md): challenge
  a substantial stable change across runtime, concurrency, security and release
  boundaries.
- [security-threat-model](../.agents/skills/security-threat-model/SKILL.md): build
  a source-grounded threat model when explicitly requested.
- [xray-fork-android-validation](../.agents/skills/xray-fork-android-validation/SKILL.md):
  qualify an accepted executable core artifact's build, bindings, native loading,
  ABI, lifecycle and cleanup within the supplied artifact/device scope.
- [xray-fork-checkpoint](../.agents/skills/xray-fork-checkpoint/SKILL.md): checkpoint
  exact reviewed owned paths under the explicitly authorized repository/ref policy.
- [xray-public-ci](../.agents/skills/xray-public-ci/SKILL.md): verify an explicitly
  authorized filtered source export and follow CI on that exact public tree.
- [handoff](../.agents/skills/handoff/SKILL.md): preserve an exact baseline, owned
  changes, validation and remaining gates for continuation.

## The eight worker roles

Main retains the human-selected model and owns scope, integration, validation
and Git. These role files define bounded assignments; their `sandbox_mode`
fields do not create a separate security boundary. Actual access comes from the
parent session's permissions.

- [mu_explorer](../.codex/agents/mu_explorer.toml): one narrow read-only code-path
  question; `gpt-6-luna`, high effort.
- [mu_investigator](../.codex/agents/mu_investigator.toml): one bounded cross-file
  or cross-subsystem technical question; `gpt-6.1-sol`, high effort.
- [mu_upstream_researcher](../.codex/agents/mu_upstream_researcher.toml): one
  upstream, dependency, licensing or external evidence lane; `gpt-6.1-sol`, high.
- [mu_go_worker](../.codex/agents/mu_go_worker.toml): an accepted disjoint Go write
  set with assigned validation; `gpt-6.1-sol`, high.
- [mu_reviewer](../.codex/agents/mu_reviewer.toml): stable-diff correctness,
  regressions and missing focused tests; `gpt-6.1-sol`, high.
- [mu_performance_reviewer](../.codex/agents/mu_performance_reviewer.toml): hot-path
  cost, allocations, contention and bounded backpressure; `gpt-6.1-sol`, high.
- [mu_critical_reviewer](../.codex/agents/mu_critical_reviewer.toml): substantial
  runtime, concurrency, security, Android and release review; `gpt-6.1-sol`, high.
- [mu_deep_reviewer](../.codex/agents/mu_deep_reviewer.toml): one named technical
  discriminator left unresolved by Sol, with its existing evidence;
  `gpt-6-astra`, high. Missing inputs or authority require those inputs, rather
  than model escalation. Only one Astra adviser is active.

Configured native capacity is 23, subject to the current session and host limits.
Use native children for bounded interactive work and the full external runtime
for durable isolated work or verified snapshot delivery. The coordinator records
the ready frontier, dependencies, slots and ownership before dispatch; capacity
is not a target worker count. See [orchestration](ORCHESTRATION.md).

## First tasks in an installed checkout

Replace the placeholders with actual project evidence. These are task patterns,
not authority to modify a checkout merely because the toolkit is installed.

**Establish scope:** “Use source root `<root>` at `<branch>/<SHA>`, compare with
adopted upstream `<SHA>`, and read contract `<path>`. Begin read-only. Report
startup facts, dirty exclusions and missing inputs before proposing changes.”

**Research:** “Use xray-fork-research to determine whether upstream `<ref>`
already handles `<trigger/behavior>`. Trace the reachable owner and consumer;
compare native reuse and the smallest justified change. Return exact evidence
and unknowns. No edits or Git operations.”

**Implement an accepted change:** “Use xray-fork-implement for `<behavior>` in
the exact write set `<paths>`, preserving `<dirty exclusions>`. Acceptance is
`<observable result>`; run `<focused checks>` through the resource guard.
Arrange independent review. Git policy is `<none/local commit/exact remote-ref>`.”

**Review:** “Review the stable diff from `<base>` to `<candidate>` against
`<contract>`, using supplied `<validation receipt>`. Report realistic triggers,
consequences and exact locations. Use adversarial-reviewer for the substantial
runtime/concurrency/security boundary. No edits or publication.”

## Tooling and local state

The distribution includes the implementations used by the guides:

- [workspace.py](../.agents/scripts/workspace.py),
  [check_core.py](../.agents/scripts/check_core.py) and
  [session.py](../.agents/scripts/session.py) configure, verify and launch the
  selected checkout. [context_diagnostics.py](../.agents/scripts/context_diagnostics.py)
  inspects bounded local context-accounting evidence.
- [dependencies.py](../.agents/scripts/dependencies.py) installs the pinned
  [analysis lock](../.agents/dependencies/analysis-lock.json) and npm locks.
  [xray_analysis.py](../.agents/scripts/xray_analysis.py) and
  [xray_mcp.py](../.agents/scripts/xray_mcp.py) route Go/package/graph tools;
  [go_mcp.py](../.agents/scripts/go_mcp.py),
  [package_map.py](../.agents/scripts/package_map.py) and
  [inspect_go.py](../.agents/scripts/inspect_go.py) provide the underlying helpers.
  Provisioned analysis dependencies include pinned gopls v0.23.0, ast-grep and
  deadcode. The configured MCP set includes Windows gopls, GitNexus, Context7 and
  Repomix when installed; Android gopls is opt-in.
- [resource_guard.py](../.agents/scripts/resource_guard.py) owns bounded command
  descendants and isolated scratch. [mcp_backend.py](../.agents/scripts/mcp_backend.py)
  manages backend deadlines, cancellation, idle eviction and initialization replay.
- [source_size.py](../.agents/scripts/source_size.py),
  [public_export.py](../.agents/scripts/public_export.py) and
  [remote_evidence.py](../.agents/scripts/remote_evidence.py) measure exact Git
  content, verify filtered exports and record ref-observation freshness.
- [orchestration.py](../.agents/scripts/orchestration.py),
  [model_router.py](../.agents/scripts/model_router.py),
  [worker_context.py](../.agents/scripts/worker_context.py) and
  [runtime_hooks.py](../.agents/scripts/runtime_hooks.py) support external admission,
  model routing and worker integration. The [runtime lock](../.agents/runtime-lock.json),
  [city configuration](../.agents/orchestration/city.toml) and
  [host example](../examples/orchestration.json) retain the complete optional flow.

Host setup generates ignored `.local/workspace/context.json` and
`.codex/config.toml` in the installed checkout. The installer records its hashes
in `.local/workspace/devkit-install.json`; prepared workers use
`.local/workspace/worker.json`. Managed scratch lives under
`.local/host/transient/`; keep lasting evidence outside scratch and outside the
public distribution. Account authentication is supplied separately. See
[configuration](CONFIGURATION.md) and [orchestration](ORCHESTRATION.md) for the
complete local-state layout and settings.

The generated context policy requests 872000 nominal tokens, 95% effective
capacity and compaction at 80% of effective capacity, scope `total`. Local
catalog checks, configuration generation and a successful launch are distinct
from authenticated model access and confirmed session adoption.

## Tests

The [distribution tests](../tests/) check toolkit packaging, audit and
installation behavior. The `test_*.py` files in
[.agents/scripts](../.agents/scripts/) exercise analysis helpers, process
lifetime, configuration, accounting, export and orchestration behavior. See
[maintenance](MAINTENANCE.md) for the guarded test commands, fixture setup and
skip reporting requirements.

These are toolkit regressions. Xray source-core tests must match the source
revision and its behavior contracts; they are outside this distribution's
payload. A source test result cannot be transferred to a different revision
merely by copying a test or installing the toolkit.

## What the evidence establishes

Distribution checks cover their recorded Python, installer/update and synthetic
protocol fixtures. Windows host results do not qualify Linux execution, an
authenticated external model run or every configured model. The Linux worker
setup and supported analysis profiles remain available, with their actual
invocation and workload results to be recorded separately.

Likewise, source/host tests, cross-builds, executable artifacts/bindings, Android
devices, network behavior, performance and release acceptance each need their
own evidence. Passing toolkit startup, a generated MCP entry or a worker's DONE
result does not establish those outcomes. The detailed limits and reporting
rules are in [workflow](WORKFLOW.md), [analysis](ANALYSIS.md) and
[maintenance](MAINTENANCE.md).
