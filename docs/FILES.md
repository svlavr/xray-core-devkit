# File reference

Use this reference to find a file's purpose, who reads it, and where to change a setting. Paths below are relative to the devkit root; links work from this page. Instructions, skills, roles and tools remain separate linked files, read when their workflow is selected rather than combined into one large prompt.

## Ownership and update rules

**Bundled** files are maintained toolkit source, settings, examples or documentation. The [manifest](../devkit-manifest.json) inventories their hashes. The installer copies `.agents/`, `.codex/agents/`, `docs/` and `examples/` into the explicitly selected source checkout. Root tools, root documentation, legal files and `tests/` stay in the distribution. It adds marked blocks to the target's `AGENTS.md` and `.gitignore`, preserving surrounding text; it does not replace them with the distribution versions.

`devkit.py update` is explicit. It replaces a managed file only if its content still matches the recorded installed version or already matches the new version; installed hashes normalize LF/CRLF differences. Conflicting local edits or modified managed blocks stop the update before writes. Removed managed files require explicit retirement review. Unmanaged files are preserved. There is no automatic synchronization with the original devkit directory, dependency upgrade or runtime upgrade.

**Project-owned inputs** come from the source owner. **Generated host state** is ignored machine-specific output. Both are listed below. Customize project rules outside managed blocks in the target's `AGENTS.md`, or make a deliberate change to a linked maintained file. Local edits to installed bundled files must be reconciled before a managed update. Regenerate generated state with its owning command rather than committing it.

## Distribution root and reader guides

- [README.md](../README.md): human entry point and quick start; read before installation.
- [AGENTS.md](../AGENTS.md): contributor scope, ownership and publication rules read by agents in this distribution. The target retains its own instructions.
- [.agents/CODEX_PACK.md](../.agents/CODEX_PACK.md): shared workflow, model routing, evidence and resource policy read at task startup; links to selected skills/contracts.
- [devkit.py](../devkit.py): distribution command for `manifest`, `verify`, `install`, `update`, `package`; maintainers edit installer policy here. Users select an explicit target and can inspect `--dry-run`.
- [devkit-manifest.json](../devkit-manifest.json): generated public file inventory/SHA256 values read by verification, packaging, installation and audit. Regenerate with `python devkit.py manifest` after reviewing public bytes. It does not hash itself.
- [audit.py](../audit.py): maintainer command checking verified payload for credential patterns, personal paths and local dependency resolutions; reports locations without matched secrets. Pattern checks do not replace content review.
- [.gitattributes](../.gitattributes): distribution Git text policy (`text eol=lf`); maintained, not installed into a target.
- [.gitignore](../.gitignore): excludes local state/config/hooks, attachments, caches, dependencies and credentials. Installer adds its own bounded target block; this file is not copied wholesale.
- [LICENSE](../LICENSE): toolkit license; read for use/redistribution terms.
- [NOTICE](../NOTICE): attribution notice; retain when redistributing.
- [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md): dependency provenance/license obligations; read before third-party installation/redistribution and update with pins.

These maintained guides are read by humans and linked workflows, not executed:

- [docs/README.md](README.md): documentation navigation/reading order.
- [docs/INSTALLATION.md](INSTALLATION.md): prerequisites, dependency/source installation and deliberate updates.
- [docs/CONFIGURATION.md](CONFIGURATION.md): project selections, generated settings, capability checks and startup.
- [docs/PROJECT_SCOPE.md](PROJECT_SCOPE.md): owner-supplied source/contract/baseline/write-set/acceptance/publication inputs.
- [docs/WORKFLOW.md](WORKFLOW.md): evidence, validation, review, accounting and checkpoint rules.
- [docs/ANALYSIS.md](ANALYSIS.md): profiles, Go helper chains, graph freshness, provenance and resource lifetime.
- [docs/ORCHESTRATION.md](ORCHESTRATION.md): optional WSL bootstrap, city/queue/workers/hooks/batches/recovery.
- [docs/ACCOUNTING_AND_EXPORT.md](ACCOUNTING_AND_EXPORT.md): catalogs, snapshots and filtered-export configuration.
- [docs/MAINTENANCE.md](MAINTENANCE.md): toolkit validation, public review and packaging.
- [docs/FILES.md](FILES.md): this inventory; update when files, consumers or edit policy change.

## Skills: task-specific instructions

Each maintained `SKILL.md` has discovery metadata. Codex reads a selected skill when its description matches a task or the human invokes it. Change that file to change its workflow. Installation grants no source access, implementation or publication authority.

- [adversarial-reviewer/SKILL.md](../.agents/skills/adversarial-reviewer/SKILL.md): substantial runtime/concurrency/security/release review.
- [handoff/SKILL.md](../.agents/skills/handoff/SKILL.md): compact continuation evidence for a requested handoff.
- [security-threat-model/SKILL.md](../.agents/skills/security-threat-model/SKILL.md): repository-grounded AppSec modeling when explicitly requested.
- [xray-code-analysis/SKILL.md](../.agents/skills/xray-code-analysis/SKILL.md): Go ownership/references/dependencies/removal evidence.
- [xray-solution-research/SKILL.md](../.agents/skills/xray-solution-research/SKILL.md): practical native/direct/external implementation comparison.
- [xray-feature-delivery/SKILL.md](../.agents/skills/xray-feature-delivery/SKILL.md): complete justified behavior through its consumer and verification.
- [xray-core-start/SKILL.md](../.agents/skills/xray-core-start/SKILL.md): read-only startup/root/ref/policy reporting.
- [xray-fork-android-validation/SKILL.md](../.agents/skills/xray-fork-android-validation/SKILL.md): accepted Android artifact/ABI/lifecycle/resource validation.
- [xray-fork-checkpoint/SKILL.md](../.agents/skills/xray-fork-checkpoint/SKILL.md): reviewed exact-path checkpoint under human-selected Git policy.
- [xray-fork-implement/SKILL.md](../.agents/skills/xray-fork-implement/SKILL.md): accepted bounded implementation/validation/review/authorized checkpoint.
- [xray-fork-research/SKILL.md](../.agents/skills/xray-fork-research/SKILL.md): source/upstream/dependency/licensing research and evidence boundaries.
- [xray-orchestration/SKILL.md](../.agents/skills/xray-orchestration/SKILL.md): early independent lanes, explicit routing and native/external ownership.
- [xray-public-ci/SKILL.md](../.agents/skills/xray-public-ci/SKILL.md): reviewed filtered export and CI for that exported source.

Read these maintained references when their owning skill requests them:

- [security-threat-model/references/output-contract.md](../.agents/skills/security-threat-model/references/output-contract.md): threat evidence/report structure.
- [xray-fork-research/references/evidence-and-output.md](../.agents/skills/xray-fork-research/references/evidence-and-output.md): research sources/output requirements.
- [xray-orchestration/references/parallel-batches.md](../.agents/skills/xray-orchestration/references/parallel-batches.md): advisory packet schema, verified capture, dispatch and results.

The ten `agents/openai.yaml` files below provide skill UI labels, short descriptions, default prompts and implicit-invocation policy. Codex skill discovery consumes them; they are separate from role TOMLs. Keep them aligned when editing the owning skill's public surface:

- [adversarial-reviewer/agents/openai.yaml](../.agents/skills/adversarial-reviewer/agents/openai.yaml)
- [handoff/agents/openai.yaml](../.agents/skills/handoff/agents/openai.yaml)
- [security-threat-model/agents/openai.yaml](../.agents/skills/security-threat-model/agents/openai.yaml)
- [xray-code-analysis/agents/openai.yaml](../.agents/skills/xray-code-analysis/agents/openai.yaml)
- [xray-core-start/agents/openai.yaml](../.agents/skills/xray-core-start/agents/openai.yaml)
- [xray-fork-android-validation/agents/openai.yaml](../.agents/skills/xray-fork-android-validation/agents/openai.yaml)
- [xray-fork-checkpoint/agents/openai.yaml](../.agents/skills/xray-fork-checkpoint/agents/openai.yaml)
- [xray-fork-implement/agents/openai.yaml](../.agents/skills/xray-fork-implement/agents/openai.yaml)
- [xray-fork-research/agents/openai.yaml](../.agents/skills/xray-fork-research/agents/openai.yaml)
- [xray-public-ci/agents/openai.yaml](../.agents/skills/xray-public-ci/agents/openai.yaml)

`xray-orchestration`, `xray-solution-research` and `xray-feature-delivery` have no bundled `agents/openai.yaml`; their discovery metadata is in their skill frontmatter.

## Native roles and policy settings

`workspace.py` reads eleven maintained roles when generating/validating `.codex/config.toml`; `session.py` passes absolute role paths to a fresh Codex invocation. Codex reads the selected definition when creating a child. Stable role names do not identify source ownership.

- [.codex/agents/mu_explorer.toml](../.codex/agents/mu_explorer.toml): narrow read-only exploration; Luna high.
- [.codex/agents/mu_investigator.toml](../.codex/agents/mu_investigator.toml): bounded cross-file investigation; Sol 6.1 high.
- [.codex/agents/mu_upstream_researcher.toml](../.codex/agents/mu_upstream_researcher.toml): external/upstream/dependency evidence; Sol 6.1 high.
- [.codex/agents/mu_solution_researcher.toml](../.codex/agents/mu_solution_researcher.toml): practical native/direct/external implementation research; Sol 6.1 high.
- [.codex/agents/mu_behavior_reviewer.toml](../.codex/agents/mu_behavior_reviewer.toml): real-caller behavior and integration verification; Sol 6.1 high.
- [.codex/agents/mu_simplicity_reviewer.toml](../.codex/agents/mu_simplicity_reviewer.toml): remove unjustified machinery without omitting justified behavior; Sol 6.1 high.
- [.codex/agents/mu_go_worker.toml](../.codex/agents/mu_go_worker.toml): assigned bounded implementation; Sol 6.1 high.
- [.codex/agents/mu_reviewer.toml](../.codex/agents/mu_reviewer.toml): correctness/regressions/tests; Sol 6.1 high.
- [.codex/agents/mu_performance_reviewer.toml](../.codex/agents/mu_performance_reviewer.toml): allocations/latency/hot paths/backpressure; Sol 6.1 high.
- [.codex/agents/mu_critical_reviewer.toml](../.codex/agents/mu_critical_reviewer.toml): concurrency/security/Android/release; Sol 6.1 high.
- [.codex/agents/mu_deep_reviewer.toml](../.codex/agents/mu_deep_reviewer.toml): one evidenced discriminator unresolved after Sol; Astra high.

Roles disable nesting. `sandbox_mode` expresses intent; actual access follows parent-session permissions. Changes to names, models, effort, language prefix or inventory must also update `workspace.py` checks/tests. Regenerate config and start a fresh session after accepted policy changes. Roles do not override the primary model.

- [.agents/orchestration/context.json](../.agents/orchestration/context.json): context policy read by `context_policy.py` and local/external setup: model family, 872000-token window, 95% effective capacity, 80% compaction threshold of that capacity, `total` scope. This is policy, not observed accounting.
- [.agents/orchestration/models.json](../.agents/orchestration/models.json): external route map consumed by model router/adviser setup; model/effort/target/pool ceilings. Edit together with role checks/city/routing docs.
- [.agents/orchestration/city.toml](../.agents/orchestration/city.toml): configure template for managed city/provider fields, 25-session ceiling, 23-worker pool, pinned roles import, suspended idle dog and pre-start hook. Registered rigs/unrelated fields are preserved; managed fields are reapplied.
- [.agents/orchestration/adviser-policy.md](../.agents/orchestration/adviser-policy.md): adviser guidance prepended with language policy to pinned native prompts in generated city directories; configure replaces those overlays.

## Dependency metadata and examples

These are maintained inputs, not installed executable dependencies:

- [.agents/dependencies/analysis-lock.json](../.agents/dependencies/analysis-lock.json): Go tool specifications, npm versions/licenses and recorded Go/Node capability baseline; `dependencies.py` reads it. It does not install Go/Node themselves.
- [.agents/dependencies/ast-grep/package.json](../.agents/dependencies/ast-grep/package.json) and [package-lock.json](../.agents/dependencies/ast-grep/package-lock.json): direct `@ast-grep/cli` pin and full npm resolution/integrity graph.
- [.agents/dependencies/gitnexus/package.json](../.agents/dependencies/gitnexus/package.json) and [package-lock.json](../.agents/dependencies/gitnexus/package-lock.json): direct GitNexus pin and full graph; review its license before use.
- [.agents/dependencies/repomix/package.json](../.agents/dependencies/repomix/package.json) and [package-lock.json](../.agents/dependencies/repomix/package-lock.json): direct Repomix pin and full npm graph.
- [.agents/runtime-lock.json](../.agents/runtime-lock.json): Linux amd64 Gas City/Beads/Dolt/complete Codex URLs, versions, hashes and required resources; explicit runtime installer input. No binary/account credential is bundled.
- [.agents/orchestration/install_runtime.py](../.agents/orchestration/install_runtime.py): Linux bootstrap command consuming runtime lock; checks hashes/archive members before fresh-prefix installation and refuses existing prefixes/command links. Creates no WSL/account/city/authentication; see [ORCHESTRATION.md](ORCHESTRATION.md).
- [examples/orchestration.json](../examples/orchestration.json): synthetic WSL distribution/user/city/`mu-core` rig/queue/worktree/tools/proxy starting point. Copy to ignored storage, edit, pass to `orchestration.py init-context`; never auto-loaded.
- [.agents/metrics/examples/modules.example.json](../.agents/metrics/examples/modules.example.json): synthetic source-owner schema for accounting; replace paths/owners in a project-owned catalog.
- [.agents/metrics/examples/public-export.example.json](../.agents/metrics/examples/public-export.example.json): synthetic allowlist/anchor/destination/CI-blob/historical-only schema. Placeholder SHA/URL are unusable selections; read exporter parser before creating actual policy.

`dependencies.py` copies npm metadata into the explicit tools root and runs `npm ci`; differing existing metadata stops installation. Upgrade direct pins and regenerated locks together, review licenses/version-specific adapters, then deliberately reinstall/verify. Keep actual `node_modules`, binaries and download caches out of Git. Runtime upgrades need a reviewed lock change and fresh installation; nothing polls releases.

## Script entrypoints and supporting modules

These maintained Python files live in `.agents/scripts/`. Some are commands, others imported helpers. Analysis-module imports may need installed local context. Commands use their own installed checkout unless documented arguments select a root. See [ANALYSIS.md](ANALYSIS.md), [CONFIGURATION.md](CONFIGURATION.md) and [ORCHESTRATION.md](ORCHESTRATION.md) for invocations/prerequisites. Edit implementations here for accepted tooling changes.

### Setup, session and shared policy

- [workspace.py](../.agents/scripts/workspace.py): `setup` generates ignored context/config; `verify` checks root/branch/baseline/settings/roles/catalog; `validate` checks skill/role policy without source startup. Used by startup/session/external preparation.
- [check_core.py](../.agents/scripts/check_core.py): read-only startup combines workspace verification, accounting and dirty paths. Run after setup; no fetch/build/indexing.
- [session.py](../.agents/scripts/session.py): verifies checkout and starts guarded Codex with explicit generated settings/absolute role paths; use for a fresh session after changes.
- [local_environment.py](../.agents/scripts/local_environment.py): imported context loader/bounded Git wrapper used by analysis; refuses absent/wrong-root context instead of borrowing another project.
- [context_policy.py](../.agents/scripts/context_policy.py): policy reader/catalog checker/TOML generator imported by workspace/external configuration.
- [language_policy.py](../.agents/scripts/language_policy.py): maintained primary/worker strings imported by workspace/worker context/dispatch/overlays; English internal reports and Russian primary human replies.
- [context_diagnostics.py](../.agents/scripts/context_diagnostics.py): explicit `--thread` command reads bounded local Codex state/rollout accounting; emits selected usage/runtime fields without prompts/credentials.
- [dependencies.py](../.agents/scripts/dependencies.py): explicit selected-tools-root `install`/`status`; consumes locks and runs guarded Go/npm installation outside checkout.

### Go, graph and MCP chain

- [xray_analysis.py](../.agents/scripts/xray_analysis.py): status/package/symbol/graph commands; root/profile/source fingerprints/caches. Graph refresh needs committed covered source; startup builds no index.
- [package_map.py](../.agents/scripts/package_map.py): command/imported guarded `go list` maps, production/test edges and reverse imports; called by package analysis.
- [inspect_go.py](../.agents/scripts/inspect_go.py): command called by symbol analysis; checks actual workspace, invokes bundled MCP/ast-grep chain, parses references and writes fresh source/build receipts.
- [mcp_probe.py](../.agents/scripts/mcp_probe.py): bounded JSON-lines probe called by inspection; raw initialization/catalog/call results, stderr and logs. Put `--args` last.
- [go_mcp.py](../.agents/scripts/go_mcp.py): stdio adapter used by Go launcher/probes/workers; explicit binary/root, gopls v0.23.0 check and version-specific one-based reference-line correction.
- [gopls_stdio.py](../.agents/scripts/gopls_stdio.py): compatibility entrypoint forwarding explicit binary/root to the same adapter.
- [xray_mcp.py](../.agents/scripts/xray_mcp.py): configured gopls/GitNexus entrypoint; checkout/profile provenance, freshness, deadlines/cancellation. Identity mode starts no backend; check actual `go_workspace` separately.
- [mcp_backend.py](../.agents/scripts/mcp_backend.py): imported sequential/persistent clients used by probe/graph gateway; initialization, response matching, deadlines and shutdown.
- [resource_guard.py](../.agents/scripts/resource_guard.py): shared subprocess owner/direct runner; marked TEMP, descendant containment, timeout/cancellation/inactive recovery and MCP idle release. Tests/builds use `--timeout ... -- <command>`; durable outputs stay outside scratch.

### Source evidence and export

- [source_size.py](../.agents/scripts/source_size.py): offline Git-blob `snapshot`/`verify`/`report`/`history`; owner catalog/baseline/snapshot inputs. Startup imports its check. INDEX and HEAD are separate evidence sources.
- [ownership_map.py](../.agents/scripts/ownership_map.py): explicit standalone HEAD/INDEX check for shared-integration maps; it first verifies the source-size snapshot, then reads the catalog-selected semantic map. Source-size verification does not automatically run this additional check.
- [remote_evidence.py](../.agents/scripts/remote_evidence.py): bounded exact-ref command/imported reuse helper; LIVE/UNAVAILABLE receipts, original observation time on reuse, no local-HEAD substitution after failure.
- [public_export.py](../.agents/scripts/public_export.py): separately authorized `prepare`/`verify`/`publish` for committed allowlisted source; project/repository policy, clean source, blobs, ancestry, destination/receipt guards before any permitted push. Installation never calls it.

### Optional external workers

- [orchestration.py](../.agents/scripts/orchestration.py): Windows host commands `init-context`, `configure`, `prepare`, `dispatch`, `batch`, `batch-status`, `status`, `start`, `stop`, `gc`; WSL boundary checks, selected config/deployment/receipts and native Gas City calls.
- [model_router.py](../.agents/scripts/model_router.py): imported route selector/resolved-config validator; dispatch/batch use explicit policy, bounded lookup and evidenced escalation.
- [agent_batch.py](../.agents/scripts/agent_batch.py): imported capture/hash verification/admission/replay for selected worktree bytes/Git blobs; submits ready native jobs and resumes identical IDs without duplicates.
- [worker_context.py](../.agents/scripts/worker_context.py): command/imported isolated setup checks base/sole local-queue origin and writes worker context/Go config without nesting. Re-runs overwrite worker host files; never use on integrator checkout.
- [provision_worker.py](../.agents/scripts/provision_worker.py): Linux pre-start hook verifies manifest/slot, invokes native pinned worktree provisioning, generates context and trusts reviewed city-bound hooks.
- [runtime_hooks.py](../.agents/scripts/runtime_hooks.py): Linux configure/pre-start helper creates/checks four reviewed hooks, verifies native inventory/fingerprints and persists trust via native Codex API. Changed/extra hooks block setup; ordinary host setup does not call it.

External configure deploys `go_mcp.py`, `resource_guard.py`, `worker_context.py`, `language_policy.py`, `provision_worker.py` and `runtime_hooks.py` into Linux and verifies hashes. These are explicit refreshed copies, not links back here. Maintained adapters expect `/usr/local/bin` commands and `/usr/local/lib/mu-runtime` helpers; changing that layout requires coordinated code/template changes, not only editing an example host path.

## Regression tests

These maintained synthetic toolkit checks run through `unittest` discovery; they are not imported Xray runtime tests. Change them when accepted behavior needs evidence. Mocked passes do not prove installed backends/authenticated model runs/Android/source release. Use guarded commands in [MAINTENANCE.md](MAINTENANCE.md). Some analysis tests require local test context; real gopls cases skip without a binary. Keep skips visible.

The nineteen `.agents/scripts/test_*.py` modules are:

- [test_agent_batch.py](../.agents/scripts/test_agent_batch.py): input bounds, frozen hashes, native admission/replay.
- [test_analysis_helpers.py](../.agents/scripts/test_analysis_helpers.py): helper chain/profiles/parsing/normalization/probe failures.
- [test_context_diagnostics.py](../.agents/scripts/test_context_diagnostics.py): bounded accounting extraction/redaction.
- [test_context_policy.py](../.agents/scripts/test_context_policy.py): arithmetic/catalog compatibility/invalid policy.
- [test_dependencies.py](../.agents/scripts/test_dependencies.py): path/alias protection before writes.
- [test_language_policy.py](../.agents/scripts/test_language_policy.py): role/primary/worker/batch language and primary-model preservation.
- [test_mcp_backend.py](../.agents/scripts/test_mcp_backend.py): sequential/persistent protocol/lifecycle/failures.
- [test_model_router.py](../.agents/scripts/test_model_router.py): routing/bounded lookup/evidenced deep escalation.
- [test_orchestration.py](../.agents/scripts/test_orchestration.py): host boundaries/archives/pins/city preservation/wave reuse.
- [test_ownership_map.py](../.agents/scripts/test_ownership_map.py): exact ownership/blob maps.
- [test_public_export.py](../.agents/scripts/test_public_export.py): allowlists/private paths/history/drift/publication guards in synthetic Git trees.
- [test_remote_evidence.py](../.agents/scripts/test_remote_evidence.py): LIVE/mismatch/UNAVAILABLE/reuse/retained failures.
- [test_resource_guard.py](../.agents/scripts/test_resource_guard.py): descendants/scratch recovery/idle release/cancellation.
- [test_runtime_hooks.py](../.agents/scripts/test_runtime_hooks.py): reviewed commands/native fingerprints/trust.
- [test_source_size.py](../.agents/scripts/test_source_size.py): blob accounting/categories/ownership/snapshots.
- [test_worker_context.py](../.agents/scripts/test_worker_context.py): queue/base/isolated configuration.
- [test_workspace.py](../.agents/scripts/test_workspace.py): setup guards/preserved edits/inventory/generated config.
- [test_xray_analysis.py](../.agents/scripts/test_xray_analysis.py): graph freshness/leases/concurrency/cancellation/retained manifests.
- [test_xray_mcp.py](../.agents/scripts/test_xray_mcp.py): real stdio with fake backends/deadlines/cancellation/cleanup, no live indexing.

Two distribution-only tests stay outside the installed payload:

- [tests/test_distribution.py](../tests/test_distribution.py): synthetic installation/updates/conflicts/aliases/preserved instructions/archives.
- [tests/test_audit.py](../tests/test_audit.py): findings/redaction/reserved negative credential fixtures.

## Project-owned inputs: create for the selected source

These entries describe the selected source project's inputs, not policies supplied by the toolkit. Follow the linked guide/parser; do not borrow another project's policies. The installer preserves source-owned instructions outside its managed block and does not generate the project policies/catalogs below. Source owners decide which belong in their repository.

- Target `AGENTS.md`, optional `AGENTS.override.md`: source instructions/task authority read by agents; durable rules outside managed blocks. The distribution's root [AGENTS.md](../AGENTS.md) governs toolkit contributors; the installer adds only its guidance block to the target's own file. See [PROJECT_SCOPE.md](PROJECT_SCOPE.md).
- `.agents/project.json`: optional user setup/publication selections read by workspace/export policy. Keys: `baseline`, `expected_branch`, `integrating_url`, `integrating_branch`, `public_url`, `public_branch`, `anchor`, `public_push_mode`; see [CONFIGURATION.md](CONFIGURATION.md). Rerun setup after branch/baseline selection. Destinations do not rewrite remotes.
- `.agents/metrics/modules.json`: reviewed actual owner catalog consumed by accounting; start from the linked example and replace synthetic owners.
- `.agents/metrics/shared-integration.json`: optional exact blob ownership/consumer map selected by catalog and checked by `ownership_map.py`.
- `.agents/metrics/source-size.json`: generated source evidence, distinct from ignored host state. Create with `source_size.py snapshot`; selected checkpoint accounting stages/verifies it with source/catalog. See [ACCOUNTING_AND_EXPORT.md](ACCOUNTING_AND_EXPORT.md) and [WORKFLOW.md](WORKFLOW.md).
- `.agents/public-export.json`: reviewed source allowlist/public destination/anchor/CI blobs/historical-only paths consumed by exporter; see [ACCOUNTING_AND_EXPORT.md](ACCOUNTING_AND_EXPORT.md) and linked example. Missing policy stops export.
- Task/contract/batch packets: owner inputs at explicit paths. Keep host paths/raw receipts/frozen bundles under ignored `.local/`; see [PROJECT_SCOPE.md](PROJECT_SCOPE.md) and [ORCHESTRATION.md](ORCHESTRATION.md).

## Generated and ignored host files

These are not bundled maintained source. Keep them untracked; never package account state or reuse another checkout's context. See [CONFIGURATION.md](CONFIGURATION.md) for setup and [ORCHESTRATION.md](ORCHESTRATION.md) for external setup.

- `.local/workspace/devkit-install.json`: installer target/managed hashes/block state; update reads/replaces after successful writes. Preserve it; editing hashes cannot safely reconcile real local modifications.
- `.local/workspace/context.json`: setup records root, selected comparison SHA/branch, executable/tools paths, remotes and config hash; startup/session/analysis read it. Rerun setup to refresh. Comparison selection is not adopted-upstream proof.
- `.codex/config.toml`: generated primary settings referencing roles/scripts. Setup refuses tracked/aliased files, unrelated existing config and locally edited generated bytes. Save/reconcile edits before regeneration; customize maintained inputs. Fresh sessions load changes.
- `.local/workspace/orchestration.json`: init-context writes explicit WSL connection/root and refuses an existing connection; orchestration reads it. Connection changes need deliberate store review.
- `.local/workspace/worker.json`, worker `context.json`/`.codex/config.toml`: isolated base/queue config consumed by workers/Go adapter; pre-start refreshes from prepared wave. Durable customization belongs in inputs/task packets.
- `.local/workspace/dispatch.json`, wave/batch receipts/input manifests, `deployed-worker-tools.json`, `city-before-configure.toml`, `orchestration-keepalive.json`: preparation/provenance/recovery/process state. Preserve failures; use status/replay/recovery instead of editing JSON to claim success.
- `.local/analysis/` and checkout-scoped analysis caches: maps/raw MCP/AST/symbol evidence, graph snapshots/indexes/registries/manifests/leases; freshness checks and humans read them. Refresh through analysis commands. Durable evidence stays outside transient scratch.
- `.local/host/transient/run-*`: disposable marked TEMP/TMP/GOTMPDIR owned by guard; recover with `resource_guard.py --clean`. Shared caches/other sessions/unmarked global TEMP are not cleanup targets.
- `.local/dist/`: optional packaged ZIP; package command refuses existing output, so select a new path.
- `.codex/hooks.json`: reviewed external document created/checked in Linux city/worker; differing content blocks setup. Ordinary Windows workspace setup does not create it.
- `.codex-remote-attachments/`, `__pycache__/`, `*.pyc`, `node_modules/`: attachments/runtime/dependency caches excluded from payload. Tools-root npm metadata are maintained-file copies, not a second editable authority.

Account-local Codex authentication, model catalogs and hook-trust state remain outside the payload. Workspace reads a local catalog without authenticating; external setup uses the dedicated Linux account. Hook trust is an explicit native API mutation. No automatic account transfer occurs. Ordinary workspace/session setup does not rewrite global host Codex settings.

## Change and verify the right layer

For source settings, edit project instructions/selections or explicit host inputs, then regenerate their owning layer. For toolkit maintenance, edit bundled source and linked instructions/tests together; run `workspace.py validate`, relevant guarded regressions and content review. Once bytes stabilize, run `devkit.py manifest`, `devkit.py verify` and `audit.py`; see [MAINTENANCE.md](MAINTENANCE.md). Manifest refresh accepts current bytes, so review must precede it.

Installed users review the distribution, run `devkit.py update --target <source-root> --dry-run`, reconcile conflicts and explicitly update. Reinstall changed dependencies separately, rerun setup when settings change and launch a fresh session. External helpers/adviser overlays change through explicit configure; runtime packages require a fresh install. Verifying one layer does not prove the others or authorize publication.
