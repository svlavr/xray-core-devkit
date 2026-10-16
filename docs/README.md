# Documentation

Xray Core DevKit is the complete configured Codex toolkit for Xray-oriented
source work. Begin with [installation](INSTALLATION.md) to copy it into a
checkout you select. Use the [file map](FILES.md) to find every distributed
component and its purpose.

## Choose the correct directory

The **DevKit root** is the download containing `devkit.py`. Run distribution
verification, installation, updates and packaging there. It is a tooling
repository, without an Xray `go.mod`.

The **source root** is the explicitly selected Xray Git checkout receiving the
toolkit. Run workspace setup, startup, sessions, Go analysis and source work
there. Its module must remain `github.com/xtls/xray-core`. Installation copies
ordinary local files; the installed checkout has no runtime dependency on the
DevKit download.

Copying the toolkit does not select a source task or grant publication
authority. The human supplies the root, task, contract, comparison baseline,
write set and Git policy through [project scope](PROJECT_SCOPE.md).

## Find the right guide

- [Installation](INSTALLATION.md): prerequisites, first copy, dependency
  provisioning, setup, fresh sessions, updates and common failures.
- [Configuration](CONFIGURATION.md): editable policy files, generated host
  settings, exact model/context/MCP values and existing-config handling.
- [File map](FILES.md): scripts, settings, skills, references, roles and tests.
- [Project scope](PROJECT_SCOPE.md): owner-supplied inputs and work authority.
- [Workflow and evidence](WORKFLOW.md): ownership, independent review, focused
  validation, source accounting and checkpoint boundaries.
- [Go and MCP analysis](ANALYSIS.md): references, imports, syntax, reachability,
  graph freshness and process lifetime.
- [Accounting and source export](ACCOUNTING_AND_EXPORT.md): owner catalogs,
  exact Git blobs, export manifests and ancestry checks.
- [External orchestration](ORCHESTRATION.md): Linux/WSL prerequisites, Gas City,
  Beads, Dolt, verified input batches, isolated workers and result integration.
- [Maintenance](MAINTENANCE.md): tooling regression contexts, public-content
  review, manifests and packaging.
- [Third-party notices](../THIRD_PARTY_NOTICES.md): component versions, provenance
  and license terms. The toolkit [license](../LICENSE) does not replace them.

The [agent pack](../.agents/CODEX_PACK.md) connects the accepted human scope to
skills, role routing and evidence policy. [AGENTS.md](../AGENTS.md) applies to
maintenance of the DevKit itself; installed source projects retain their own
human instructions.

## Skills and roles

Each skill is an actual entrypoint with separately maintained references and
scripts. Those linked files are part of the distribution.

- [xray-core-start](../.agents/skills/xray-core-start/SKILL.md): report selected
  root, branch/HEAD, baseline, remotes, policy and dirty paths without starting
  implementation, indexing or publication.
- [xray-fork-research](../.agents/skills/xray-fork-research/SKILL.md): investigate
  upstream behavior, dependencies, licensing and source evidence.
- [xray-solution-research](../.agents/skills/xray-solution-research/SKILL.md):
  compare native, direct and external implementations before choosing machinery.
- [xray-feature-delivery](../.agents/skills/xray-feature-delivery/SKILL.md): finish
  justified consumer behavior, including integration and independent verification.
- [xray-design-exploration](../.agents/skills/xray-design-exploration/SKILL.md):
  complete alternatives, independent premise criticism and factual research.
- [xray-decision-experiment](../.agents/skills/xray-decision-experiment/SKILL.md):
  acceptance design, owned actual experiments and creator/critic feedback.
- [xray-agent-evaluation](../.agents/skills/xray-agent-evaluation/SKILL.md):
  executable outcome and workflow comparisons with evaluator validity checks.
- [xray-protocol-compatibility](../.agents/skills/xray-protocol-compatibility/SKILL.md):
  selected config/wire/transport and named-peer compatibility through its caller.
- [xray-runtime-qualification](../.agents/skills/xray-runtime-qualification/SKILL.md):
  progressive concurrency, security, build/ABI and measured-performance modes.
- [xray-code-analysis](../.agents/skills/xray-code-analysis/SKILL.md): trace Go
  ownership, references, consumers and removal questions for the selected build.
- [xray-fork-implement](../.agents/skills/xray-fork-implement/SKILL.md): implement
  an accepted bounded slice, validate it and arrange independent review.
- [xray-orchestration](../.agents/skills/xray-orchestration/SKILL.md): dispatch
  useful independent lanes early and coordinate verified worker inputs/results.
- [adversarial-reviewer](../.agents/skills/adversarial-reviewer/SKILL.md): challenge
  substantial changes across runtime, concurrency, security and release boundaries.
- [security-threat-model](../.agents/skills/security-threat-model/SKILL.md): build
  a source-grounded threat model when explicitly requested.
- [xray-fork-android-validation](../.agents/skills/xray-fork-android-validation/SKILL.md):
  qualify an accepted executable core artifact within its build/device scope.
- [xray-fork-checkpoint](../.agents/skills/xray-fork-checkpoint/SKILL.md): checkpoint
  reviewed owned paths under explicit repository/ref authority.
- [xray-public-ci](../.agents/skills/xray-public-ci/SKILL.md): verify an authorized
  filtered source export and follow CI on that exact public tree.
- [handoff](../.agents/skills/handoff/SKILL.md): preserve exact source, owned
  changes, evidence and remaining gates for continuation.

Main keeps the human-selected primary model and owns integration, validation
and Git. Nineteen domain roles provide bounded assignments:

- [mu_explorer](../.codex/agents/mu_explorer.toml): one narrow read-only code path;
  `gpt-6-luna`, high.
- [mu_investigator](../.codex/agents/mu_investigator.toml): one bounded technical
  question spanning files or subsystems; `gpt-6.1-sol`, high.
- [mu_upstream_researcher](../.codex/agents/mu_upstream_researcher.toml): external,
  upstream, dependency or licensing evidence; `gpt-6.1-sol`, high.
- [mu_solution_researcher](../.codex/agents/mu_solution_researcher.toml): practical
  implementation comparison and deciding experiments; `gpt-6.1-sol`, high.
- [mu_innovator](../.codex/agents/mu_innovator.toml): complete technical
  alternatives and falsifiable mechanisms; `gpt-6.1-sol`, high.
- [mu_design_critic](../.codex/agents/mu_design_critic.toml): independent premise
  and design criticism before implementation; `gpt-6.1-sol`, high.
- [mu_test_architect](../.codex/agents/mu_test_architect.toml): consumer acceptance,
  deciding experiments and evaluator controls; `gpt-6.1-sol`, high.
- [mu_agent_evaluator](../.codex/agents/mu_agent_evaluator.toml): complete outcomes,
  provenance and workflow evidence adjudication; `gpt-6.1-sol`, high.
- [mu_protocol_reviewer](../.codex/agents/mu_protocol_reviewer.toml): config-to-wire
  and peer interoperability controls; `gpt-6.1-sol`, high.
- [mu_concurrency_reviewer](../.codex/agents/mu_concurrency_reviewer.toml): resource
  transitions, cancellation, locks and progress guarantees; `gpt-6.1-sol`, high.
- [mu_security_reviewer](../.codex/agents/mu_security_reviewer.toml): reachable
  attacker input, trust boundaries and sensitive sinks; `gpt-6.1-sol`, high.
- [mu_build_qualifier](../.codex/agents/mu_build_qualifier.toml): selected Go/OS/ABI
  and native-consumer qualification; `gpt-6.1-sol`, high.
- [mu_behavior_reviewer](../.codex/agents/mu_behavior_reviewer.toml): verify changed
  behavior through its real caller; `gpt-6.1-sol`, high.
- [mu_simplicity_reviewer](../.codex/agents/mu_simplicity_reviewer.toml): challenge
  unnecessary machinery while preserving justified behavior; `gpt-6.1-sol`, high.
- [mu_go_worker](../.codex/agents/mu_go_worker.toml): an accepted disjoint Go write
  set and its validation, or explicitly assigned experimenter mode;
  `gpt-6.1-sol`, high.
- [mu_reviewer](../.codex/agents/mu_reviewer.toml): stable-diff correctness,
  regressions and focused test gaps; `gpt-6.1-sol`, high.
- [mu_performance_reviewer](../.codex/agents/mu_performance_reviewer.toml): hot-path
  measurement design or independent cost/load/backpressure review;
  `gpt-6.1-sol`, high.
- [mu_critical_reviewer](../.codex/agents/mu_critical_reviewer.toml): runtime,
  concurrency, security, Android and release review; `gpt-6.1-sol`, high.
- [mu_deep_reviewer](../.codex/agents/mu_deep_reviewer.toml): one evidenced technical
  discriminator unresolved by Sol; `gpt-6-astra`, high, one active adviser.

Capacity 23 is a configured bound, subject to observed session/host limits.
Native children do not spawn children. Role `sandbox_mode` fields express
intent; the parent session's actual permissions govern access. Missing inputs,
authority or model access require those inputs, rather than a stronger model.

## First task after startup

Supply concrete evidence instead of leaving these placeholders unresolved:

> Use source root `<root>` at `<branch>/<SHA>` and contract `<path>`. The adopted
> upstream comparison is `<SHA>`. Begin read-only and report dirty exclusions,
> reachable owners and missing inputs. The authorized work is `<behavior>` in
> `<write set>` with acceptance `<observable result>`, checks `<commands>` and Git
> policy `<none/local commit/exact remote-ref>`.

Choose research, implementation, review, artifact validation or handoff from the
skills above. Installation and a passing startup do not authorize a task by
themselves. Keep source/host, artifact, device, network, performance and release
outcomes separate; [workflow](WORKFLOW.md) explains the evidence boundaries.
