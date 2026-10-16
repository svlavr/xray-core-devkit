# Install the full configured toolkit

Installation has four steps: copy the toolkit into a source checkout, provision
analysis dependencies, generate checkout-local settings, then launch a fresh
Codex session. The external worker runtime has its own setup. All thirteen skills,
eleven roles and supporting workflows are included in the copy.

## Requirements and paths

Use Windows for the primary arrangement documented here. Linux external workers
use the separate runtime described in [orchestration](ORCHESTRATION.md). macOS
process supervision and arbitrary Codex-compatible clients are not qualified.

Before starting, supply:

- Python 3.11+ and Git on PATH.
- Go and Node with npm on PATH for dependency installation. The
  [analysis lock](../.agents/dependencies/analysis-lock.json) records reference
  Go `go1.27.0` and observed Node `v24.18.0`; provisioning discovers your existing
  executables and does not install or enforce those host toolchain versions.
- A Codex CLI supporting the generated multi-agent, context and MCP settings,
  plus your own authentication and access to the configured models. The pinned
  Linux Codex asset in the runtime lock does not install the Windows CLI.
- Network access for Go/npm downloads and the remote Context7 and grep.app MCP endpoints.
- A separately selected Xray Git checkout, on a named branch with an initial
  commit. Its Go module must be exactly `github.com/xtls/xray-core`.

Use canonical absolute paths without symlink/junction aliases. The examples use
`D:/Work/Xray-core` for the **source root** and `D:/Tools/xray-analysis` for tools.
The **DevKit root** is the download containing `devkit.py`; it cannot serve as
the Xray source root. Check [file locations](FILES.md) if unsure which directory
owns a command.

The analysis dependencies are gopls `v0.23.0`, deadcode `v0.50.0`, GitNexus
`1.6.12`, Repomix `1.18.1` and ast-grep CLI `0.45.3`. npm transitive versions and
tarball integrity are recorded in included package locks. The gopls adapter's
reference-line correction is specific to its pinned release. Review
[third-party notices](../THIRD_PARTY_NOTICES.md), including GitNexus's
noncommercial terms. No dependency binaries or account credentials are bundled.

## 1. Copy the shared files

Clone the repository or extract the ZIP. Open the DevKit root and verify it:

```powershell
python devkit.py verify
```

```powershell
python audit.py
```

Preview exactly which target files would be written:

```powershell
python devkit.py install --target D:/Work/Xray-core --dry-run
```

Apply the copy after reviewing that output:

```powershell
python devkit.py install --target D:/Work/Xray-core
```

The payload includes `.agents/`, `.codex/agents/`, `docs/` and `examples/`.
Installation adds marked guidance to `AGENTS.md` and ignore rules to `.gitignore`,
preserving unrelated human text. It writes a local hash receipt at
`.local/workspace/devkit-install.json`. It does not run setup, install packages,
select remotes, change source files or alter global Codex/account settings.
Source-owned extra skills and roles are preserved; validation reports them
separately from the required thirteen skills and eleven managed roles.

Conflicts are checked before payload writes. Identical existing files are
accepted; differing existing tooling is preserved and blocks the copy. There is
no force-overwrite switch. Reconcile each conflict before retrying. Use `update`
when a target already has an install receipt.

## 2. Install or reuse analysis tools

Change to the installed source root:

```powershell
cd D:/Work/Xray-core
```

Install the complete locked dependency set into your selected tools directory:

```powershell
python .agents/scripts/dependencies.py install --tools D:/Tools/xray-analysis
```

Inspect the resulting layout, or inspect an existing matching installation
before deciding to reuse it:

```powershell
python .agents/scripts/dependencies.py status --tools D:/Tools/xray-analysis
```

Provisioning builds gopls and deadcode with `go install`, runs `npm ci` for
GitNexus, Repomix and ast-grep, then copies ast-grep's binary into `bin/`. These
upstream npm packages can execute their native installation steps. Tools are
installed under the selected root:

```text
xray-analysis/
  bin/          gopls, deadcode, ast-grep
  gitnexus/     locked npm installation
  repomix/      locked npm installation
  ast-grep/     locked npm installation
  cache/        generated checkout-keyed analysis evidence
```

`status` reports Go binary presence and npm package metadata/version matches;
it does not execute tools or establish server readiness. If dependency metadata
conflicts with the lock, installation stops. For a changed lock set, choose a
new tools directory and explicitly select it in setup. A failed download or
build requires its actual diagnostic and a successful retry, not a generated
server entry presented as success. Shared Go caches remain outside scratch.

## 3. Generate and verify checkout settings

Still in the source root:

```powershell
python .agents/scripts/workspace.py setup --analysis-tools D:/Tools/xray-analysis
```

```powershell
python .agents/scripts/workspace.py verify
```

```powershell
python .agents/scripts/check_core.py
```

Setup generates ignored `.local/workspace/context.json` and `.codex/config.toml`.
It selects local HEAD as a comparison baseline unless an explicit
`--baseline <full-40-character-SHA>` or `.agents/project.json` selects another
local ancestor. This default is not evidence of an adopted official upstream
base. Startup reports the root, branch, HEAD, selected baseline, remotes and
dirty paths. Fresh source accounting is explicitly `UNINITIALIZED` until the
owner supplies its catalog/snapshot.

The local model catalog is checked if available. Absence is `UNKNOWN`; an
incompatible catalog stops verification. Neither result authenticates your
account. Existing manual Codex configuration is preserved and can block setup;
follow [configuration](CONFIGURATION.md#existing-local-configuration) before
regenerating it.

## 4. Start a fresh session

From the installed source root:

```powershell
python .agents/scripts/session.py --
```

The launcher verifies the local layer, passes it to `codex` as invocation
settings and launches in the source root. Use your usual authentication and
project trust flow. It does not override the parent model or effort. A launched
process alone does not prove model access or successful MCP calls. Before Go
analysis, verify the actual `go_workspace` through the selected server/profile;
see [analysis](ANALYSIS.md).

Role, settings and MCP launcher changes require fresh processes. Starting a new
session does not restart another active chat. Editing generated config directly
blocks later verification; edit its maintained source instead, as explained in
[configuration](CONFIGURATION.md#editable-inputs-and-generated-state).

## External orchestration

The complete Gas City/Beads/Dolt/Codex runtime is retained. Its checksum-pinned
Linux amd64 assets use the separate `.agents/runtime-lock.json`. Supply your own
selected Linux/WSL environment, city, user, local queue, analysis tools and login.
Follow [ORCHESTRATION.md](ORCHESTRATION.md) for bootstrap, admission, verified
input batches and result collection. Existing environments are not selected or
altered automatically. Main integrates worker commits; workers cannot publish
to GitHub.

## Update an installed checkout

Obtain a newer reviewed DevKit through a fresh download or a normal pull in
your DevKit clone. Updates do not retrieve new versions themselves. From that
DevKit root, preview and apply:

```powershell
python devkit.py update --target D:/Work/Xray-core --dry-run
```

```powershell
python devkit.py update --target D:/Work/Xray-core
```

The updater checks the target receipt and refuses locally changed managed files
or changed managed instruction blocks. Text outside those blocks remains
intact. Removed upstream payload paths require explicit retirement review; the
updater does not delete them. No installed file depends on the download remaining
available after the copy.

Then return to the source root and rerun setup with your chosen tools root:

```powershell
cd D:/Work/Xray-core
```

```powershell
python .agents/scripts/workspace.py setup --analysis-tools D:/Tools/xray-analysis
```

```powershell
python .agents/scripts/check_core.py
```

```powershell
python .agents/scripts/session.py --
```

Setup regeneration does not update dependencies. If the analysis lock changed,
first install the new set into a new tools directory and pass that directory to
setup. If you selected a different comparison baseline, pass it again or keep
it in `.agents/project.json`: rerunning setup without either selects current
HEAD. See [configuration](CONFIGURATION.md) for branch and baseline guards.

## Troubleshooting

- **Public manifest mismatch:** the DevKit bytes differ from their manifest.
  Users should obtain an intact reviewed copy. Maintainers refresh the manifest
  only after reviewing changes; see [maintenance](MAINTENANCE.md).
- **Use update/install:** use `update` for a target with a receipt, and `install`
  for a new target. Do not remove the receipt to bypass a conflict.
- **Conflicting managed files:** preserve your local version, compare it with
  the incoming file and reconcile deliberately before retrying. The installer
  has no automatic merge or force mode.
- **Wrong module, detached HEAD or branch mismatch:** use the intended source
  checkout and named branch, then run setup for that choice. A baseline must be
  a full locally available ancestor SHA; setup does not fetch it.
- **Existing/edited Codex config or unignored host files:** follow the
  [configuration recovery procedure](CONFIGURATION.md#existing-local-configuration).
  Do not track host settings to make verification pass.
- **Interrupted setup:** rerun the same setup command with the intended tools
  root and baseline. Known generated files are recovered through the saved
  digest; arbitrary manual edits are still preserved and rejected. Setup also
  requires its `.local/workspace/.setup-probe.tmp` location to be ignored.
- **Codex CLI unavailable:** put your compatible Windows CLI on PATH, then
  launch a fresh session. Linux runtime bootstrap is a separate operation.
- **Dependency metadata or executable missing:** inspect `dependencies.py status`
  and the failed installer diagnostic. Configuration verification does not run
  the backend. Test the needed tool in its actual root/profile.
- **Model catalog unknown/incompatible:** check the catalog source and required
  models. An absent catalog is missing local evidence; model login/access still
  needs its own successful operation. Do not lower policy values merely to hide
  a capability mismatch.

Toolkit checks cover tooling and synthetic fixtures only. Real Xray behavior,
Android artifacts/devices, network routes, performance, authenticated workers
and releases require their own exact-source evidence.
