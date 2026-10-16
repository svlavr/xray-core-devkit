# Install the full configured toolkit

The working host arrangement uses Python 3.11+, Git, Go 1.27.0, Node 24.18.0,
Codex and the analysis versions recorded in `.agents/dependencies/analysis-lock.json`.
The gopls adapter deliberately requires **gopls v0.23.0** because its reference-line
normalization is specific to that release. Node/npm packages are fixed by the
included package locks, including their transitive tarball integrity values.
No application source, native binary, account credentials or captured data is
bundled. Dependencies are obtained from their upstream distributions.

The supported arrangement is the current Windows toolchain and Linux external
workers. Choose a real source checkout with a named branch and an initial commit.
The module must remain `github.com/xtls/xray-core`. The toolkit repository itself
is not an Xray module and must not be used as a source-checkout substitute.

## Install the shared files

From the downloaded DevKit root:

```powershell
python devkit.py verify
python audit.py
python devkit.py install --target D:/Work/Xray-core --dry-run
python devkit.py install --target D:/Work/Xray-core
```

Installation copies the complete `.agents` tools, skills, dependencies and
orchestration configuration, `.codex/agents`, supporting docs and examples.
It adds marked guidance to `AGENTS.md` and ignore rules to `.gitignore` while
preserving unrelated text. It writes a local hash receipt in
`.local/workspace/devkit-install.json`. It changes neither remotes nor source
files, global Codex settings or account state. A conflict is reported before
payload writes. Resolve conflicting existing tooling explicitly rather than
forcing an overwrite. Installation does not run setup or publish anything.

## Install or reuse the analysis tools

From the selected Xray checkout:

```powershell
python .agents/scripts/dependencies.py install --tools D:/Tools/xray-analysis
python .agents/scripts/dependencies.py status --tools D:/Tools/xray-analysis
```

The installer builds gopls and deadcode in the chosen `bin` directory and uses
`npm ci` with the recorded locks for GitNexus, Repomix and ast-grep. Native npm
installation steps are part of those tools' upstream packages. Failure leaves
its actual diagnostic output; a lock or configured entry is not runtime proof.
`status` reads installed metadata and file presence and explicitly reports that
it does not exercise the servers. Existing conflicting dependency manifests
are preserved and stop installation. Choose a new tools directory for a changed
dependency set, then select it explicitly in workspace setup.

The tools layout is:

```text
xray-analysis/
  bin/             gopls, deadcode, ast-grep
  gitnexus/        locked npm installation
  repomix/         locked npm installation
  ast-grep/        locked npm installation
  cache/           checkout-keyed generated analysis evidence
```

Package and symbol inspection helpers are included in `.agents/scripts`.
They use the explicit checkout and selected tools root, not scripts from the
original developer's machine. Shared Go caches remain outside disposable scratch.

## Configure and start Codex

```powershell
python .agents/scripts/workspace.py setup --analysis-tools D:/Tools/xray-analysis
python .agents/scripts/workspace.py verify
python .agents/scripts/check_core.py
python .agents/scripts/session.py --
```

Setup selects the current local HEAD as a comparison baseline unless the user
supplies `--baseline <full-SHA>`. An adopted official upstream revision must be
selected from actual project evidence; the default is not proof of adoption.
Generated context and Codex config are checkout-local and ignored. Existing
manual config is preserved; see [configuration](CONFIGURATION.md).

Use the user's existing Codex authentication. A missing local model catalog is
reported as UNKNOWN; an incompatible available catalog is rejected. These
checks do not prove online account access. Start a fresh session after role or
launcher updates and verify the actual `go_workspace` before using Go evidence.

## External orchestration

The complete Gas City/Beads/Dolt/Codex runtime is described in
[ORCHESTRATION.md](ORCHESTRATION.md). Bootstrap uses the separate checksum-pinned
`.agents/runtime-lock.json`. Supply your own Linux/WSL environment, city, user,
analysis tools, local queue and authentication. Existing project environments
are never selected or altered automatically. Main remains the integrating
owner; external workers exchange local commits and cannot publish to GitHub.

## Update

From a newer reviewed DevKit copy, use `devkit.py update --target ... --dry-run`
and then repeat without `--dry-run`. The updater preserves local edits and
requires explicit reconciliation of conflicts or retired files. It does not
delete files automatically. Installed references are ordinary local files;
the installed checkout has no runtime link to this toolkit checkout.

## Qualification boundary

The local checks exercise Python regressions, installation/update safety and
small synthetic Xray-module protocol fixtures. A particular real project, its
network route, Android artifact, external authenticated worker run or release
requires its own evidence. This shared toolkit does not carry another project's
historical acceptance or fixture exceptions.
