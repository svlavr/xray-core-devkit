# Checkout configuration and startup

Install the complete toolkit into a user-owned Xray checkout with the root installer. The supported source module is exactly `github.com/xtls/xray-core`. Python 3.11 or newer is required. Generated settings remain in the checkout; setup does not change global Codex settings, authentication, remotes, Git configuration or shared worktree exclusions.

Run from the installed Xray checkout:

```powershell
python .agents/scripts/workspace.py setup --analysis-tools C:/Tools/xray-analysis
python .agents/scripts/workspace.py verify
python .agents/scripts/check_core.py
python .agents/scripts/session.py --
```

`setup` records the resolved source root, current named branch, full current HEAD as the selected comparison baseline, Python/Git/Node paths, analysis-tools root and observed fetch/push remotes in `.local/workspace/context.json`. It creates `.codex/config.toml`. Both paths must already be ignored and untracked. The installer supplies the ignore rules; setup respects existing rules and never edits `.git/info/exclude`, including in linked worktrees. It preserves source/index changes. Remotes are observations, not configured destinations.

Use `--baseline <full-40-character-SHA>` to select a different comparison commit. The commit must exist locally and be an ancestor of HEAD. This selection is not evidence of an officially adopted upstream base. Setup records the current branch; verification rejects a subsequent branch mismatch until setup is run for the newly selected branch. Detached HEAD is rejected. Setup does not fetch or resolve remote branches.

Existing local Codex configuration without toolkit context is preserved and causes setup to stop. Preserve or incorporate that configuration before installation. Manual edits to a previously generated config are also preserved and block regeneration; move the edited file aside after saving it, then regenerate. Configuration files cannot be tracked, symbolic links, hardlink aliases or paths below reparse-point directories.

## Optional project selections

The user may create `.agents/project.json`. Supported keys are `baseline`, `expected_branch`, `integrating_url`, `integrating_branch`, `public_url`, `public_branch`, `anchor` and `public_push_mode`; values must be nonempty strings. There are no preconfigured fork URLs, private branches or private document dependencies.

Project branch/baseline values are setup defaults and guards. An explicit setup baseline takes precedence; the ignored context retains that selection until setup is rerun. Destination fields are optional explicit project policy and never rewrite remotes. Export remains a separate operation requiring an explicit `.agents/public-export.json` manifest. Only explicit `public_push_mode: "filtered-export-only"` can allow that exporter's publication guard; setup never publishes anything.

## Complete Codex settings

The generated layer keeps 11 skills and 8 domain roles. Native capacity is configured to 23, subject to actual host/session limits. Exploration uses `gpt-6-luna` at high effort, ordinary worker/review roles use `gpt-6.1-sol` at high effort, and the deep reviewer uses `gpt-6-astra` at high effort for a named unresolved discriminator. Nested native workers are disabled. The parent model and effort are not overridden. Internal tasks, analysis summaries and reports use English; only the primary coordinator's direct replies to the human use Russian.

The retained context policy requests 872000 tokens, 95 percent effective capacity and compaction at 80 percent of that effective capacity: 662720 tokens, scope `total`. Verification checks the local Codex `models_cache.json` if present. An absent catalog is explicitly `UNKNOWN`, not a successful account/model-access check. An incompatible catalog blocks verification. `--catalog <path>` chooses a read-only catalog, and `--require-capabilities` makes its absence an error. Setup does not authenticate or make online capability requests. Configuration alone does not prove an existing session loaded these settings; launch a fresh session with `session.py`. The context diagnostics command reads bounded local accounting evidence and never outputs prompts or credentials.

Windows Go/gopls, GitNexus and Context7 MCP profiles are enabled. Android Go/gopls is installed but disabled by default. Repomix is enabled when both its installed backend and a Node executable are available. The analysis-tools provisioning and version diagnostics are separate from configuration generation; generated server entries do not prove that dependencies, network access or authenticated services are available. No startup indexing or build matrix runs.

The session launcher passes checkout settings as per-invocation arguments, including absolute role paths. It preserves global settings and account authentication. Codex may require the user's usual project trust/setup before enabling project tools.

## Source accounting

Fresh official checkouts have no fork-specific owner catalog or snapshot. Startup reports source accounting as `UNINITIALIZED` until the user supplies `.agents/metrics/modules.json` and `.agents/metrics/source-size.json` through the source accounting workflow. Optional shared integration ownership lives in `.agents/metrics/shared-integration.json`. An uninitialized report is explicit missing evidence, not fabricated verification; it does not prevent ordinary toolkit startup. Catalog/snapshot validation errors remain failures after accounting is initialized.
