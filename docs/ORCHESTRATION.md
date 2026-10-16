# External orchestration

This optional Windows-to-WSL lane uses Gas City sessions, Beads work and Dolt
storage. Native Codex children remain available independently. Nothing connects
to a city until the user creates the ignored host context. The examples contain
synthetic paths. Role and pool names beginning with `mu-` are configurable naming
conventions, not a connection to another repository.

## Pinned runtime and prerequisites

`.agents/runtime-lock.json` pins Linux amd64 Gas City 1.5.0, Beads 1.3.1,
Dolt 2.4.2 and the complete Codex rust-v0.162.0-alpha.2 package by URL and SHA256.
The roles import in `.agents/orchestration/city.toml` is also commit-pinned.
Do not use an unpinned curl-to-shell installer or replace an existing runtime.

The user must explicitly prepare a dedicated WSL2 Linux amd64 distribution,
unprivileged Linux user, outbound network access, sufficient RAM/disk and
Python 3.12+. On an Ubuntu/Debian distribution, install the operating-system
prerequisites inside that selected distribution:

```sh
sudo apt-get update
sudo apt-get install python3 ca-certificates git tmux jq procps lsof util-linux
```

Use Linux filesystem directories, with no Windows drive mounts available to the
worker. The user's selected distribution must contain this `/etc/wsl.conf`:

```ini
[automount]
enabled=false
[interop]
enabled=false
appendWindowsPath=false
```

After editing that distribution's file, terminate only that distribution from
Windows (`wsl --terminate Xray-Workers`) and reopen it. Do not reuse that example
name without selecting it yourself. `orchestration.py` checks the effective UID,
configuration and live mounts before dispatch. A VM-wide WSLInterop registration
can coexist with disabled per-distribution interop; this check does not claim a
separate kernel or a complete security sandbox.

Transfer the devkit scripts and runtime lock into a new Linux staging directory
through `\\wsl.localhost\<distribution>\home\<user>\<staging>` from Windows.
Do not enable drive mounts merely to access the source. With a staging copy at
`$HOME/devkit-bootstrap`, install exact locked runtime bytes:

```sh
cd "$HOME/devkit-bootstrap"
sudo python3 .agents/orchestration/install_runtime.py \
  --lock .agents/runtime-lock.json \
  --prefix /opt/xray-devkit-runtime --bin-dir /usr/local/bin
/usr/local/bin/gc version
/usr/local/bin/bd version
/usr/local/bin/dolt version
/usr/local/bin/codex --version
```

The installer downloads every locked archive, checks its SHA256, rejects archive
escapes and preserves the complete Codex package resource tree, including its
code-mode host, `rg` and `bwrap`. It refuses existing prefixes and existing command
links. It creates no distribution, account, city, queue, authentication or agent
session. A failed install may leave a partial newly created prefix after a local
filesystem error; inspect it and select a fresh destination before retrying.

Install the Go toolchain required by the target checkout (the current template
uses Go 1.27.0) and Node 24.18.0. The Linux worker analysis tools use the same
portable dependency installer as the host:

```sh
python3 .agents/scripts/dependencies.py install --tools "$HOME/xray-tools"
```

The tool pins include gopls v0.23.0. Run `python3 .agents/scripts/dependencies.py status --tools "$HOME/xray-tools"`
and the dependency verification documented in `docs/INSTALLATION.md`. A worker needs `$HOME/xray-tools/bin/gopls` and Go on its Linux
PATH; Windows gopls binaries cannot substitute for Linux worker tools. Configure
Git identity inside this dedicated user account before allowing worker commits.
Complete `/usr/local/bin/codex login` interactively using the user's own account.
Credentials stay in Linux `$HOME/.codex` and never enter examples, source bundles,
queues or commits. Run Codex once to obtain its current `models_cache.json`.
`configure` verifies that Luna, Sol 6.1 and Astra support the maintained context
policy before admitting these settings. Unsupported access or changed context
capabilities block setup and need an explicit policy review.

## Select a new host connection

Copy `examples/orchestration.json` to an ignored local editing location, choose
its distribution, user, city, local bare queue, rig, worker worktree base and
analysis-tools paths, and optionally set a credential-free HTTP(S) proxy endpoint.
All stores except a rig beneath its city must be disjoint. Keep the rig name
`mu-core` with this maintained policy. The orchestration adapter and model target
map deliberately use that name consistently; changing it requires updating those
settings together. From the Windows integration checkout:

```powershell
python .agents/scripts/orchestration.py init-context .local/edited-orchestration.json
```

This generates `.local/workspace/orchestration.json` with the current checkout
root. It refuses to overwrite an existing connection. Host values, proxy settings,
model caches and receipts remain ignored. `init-context` performs no WSL call.
This adapter is a Windows host entrypoint; its external runtime runs in WSL.

## Initialize the independent queue, city and rig

Complete project setup first so `workspace.py` accepts the intended repository,
current branch and baseline. Commit the source/tool state selected for workers;
read-only batches can separately capture bounded dirty source bytes. Do not reuse
another project's queue or city. Create the following initial bundle from the
Windows integration checkout, using the configured **local expected branch**:

```powershell
$sourceBranch = 'codex/integration' # replace with workspace policy expected_branch
$sourceHead = git rev-parse HEAD
git -c gc.auto=0 -c maintenance.auto=false bundle create .local/workspace/seed.bundle $sourceBranch
```

Use the selected WSL UNC share to copy that bundle to the Linux user's staging
directory. In the new Linux account, adapt these paths to the ignored host
context. These commands create new objects; an existing destination requires
inspection instead of reinitialization:

```sh
sudo install -d -m 755 -o "$(id -un)" -g "$(id -gn)" \
  /srv/xray-city /srv/xray-worktrees /srv/xray-queues
# Choose queue_origin /srv/xray-queues/source.git in your host context.
source_branch=codex/integration  # same expected_branch as the exported bundle
/usr/bin/git -c gc.auto=0 -c maintenance.auto=false init --bare /srv/xray-queues/source.git
/usr/bin/git --git-dir=/srv/xray-queues/source.git fetch \
  "$HOME/devkit-bootstrap/seed.bundle" "$source_branch:refs/heads/$source_branch"
/usr/bin/git --git-dir=/srv/xray-queues/source.git symbolic-ref HEAD "refs/heads/$source_branch"
/usr/bin/git clone /srv/xray-queues/source.git /srv/xray-city/mu-core
/usr/local/bin/gc init /srv/xray-city --template minimal --providers codex --default-provider codex
```

The rig's only remote
must be the absolute local queue path, for both fetch and push. No GitHub remote,
credential helper, private integration URL or personal source state is sent to
workers by the setup adapter. The source bundle itself contains the selected
branch's reachable history; review that history before transferring it.

Then run `configure` from Windows. It preserves registered rigs and unrelated
settings, installs the maintained helpers into `/usr/local/lib/mu-runtime`, adds
the pinned rig roles import and city-scoped adviser directories, validates the
explicit model policy, and trusts only the four exact reviewed native hooks.
It creates missing hooks from the reviewed GC 1.5 template; a changed or extra
existing hook blocks setup. Native fingerprints are derived from the reviewed
commands with the selected city path and checked against Codex's native inventory.

```powershell
python .agents/scripts/orchestration.py configure
```

Register the new rig from Linux only after that configure operation has installed
the default pinned roles import:

```sh
/usr/local/bin/gc --city /srv/xray-city rig add /srv/xray-city/mu-core --name mu-core --prefix xr
/usr/local/bin/gc --city /srv/xray-city config show
```

Verify the new rig's resolved pack pin, local queue remotes, models, helpers and
paths before the first run. If initialization installed any unexpected LLM role,
suspend it explicitly before starting. Only then, from Windows:

```powershell
python .agents/scripts/orchestration.py configure
python .agents/scripts/orchestration.py prepare
python .agents/scripts/orchestration.py start
python .agents/scripts/orchestration.py status
```

`prepare` rejects active/pending rig work and dirty committed-source inputs. It
exports the exact integration HEAD through a Git bundle into the local queue,
checks the transferred commit, records a persistent wave/bead ID, and provisions
all 23 source-pinned native GC worktrees before admitting the worker pool config.
Its manifest includes the city, source SHA, generation, queue, worktree base and
analysis-tools root. Each pre-start revalidates the slot and local queue, generates
worker-only ignored context, and verifies/trusts the exact city-bound hooks.
Workers read `docs/PROJECT_SCOPE.md` and their dispatched write set. They may
create local handoff commits and exchange them only with this local queue.
Integration, review and publication belong to the main coordinator.

## Dispatch, inspect and resume

Model routing is explicit: bounded lookup uses Luna High; ordinary implementation
and wider analysis/review use Sol 6.1 High. A named technical discriminator still
unresolved after a Sol attempt, with its evidence attached, may enter the single
Astra High city-scoped pool. Missing files, access and unrun validation request
context instead of escalating. An unchanged Astra question is not repeated.
Worker pools are bounded to 23. The city-wide session ceiling is 25, including the
coordinator and deterministic dispatcher; capacity is a ceiling, not a launch quota.

A one-task packet contains `kind`, a one-line `title` and a scoped `body`.
Implementation targets `mu-core/codex` and needs a prepared source wave. Adviser
packets must identify Linux-readable evidence. Do not pass Windows paths:

```powershell
python .agents/scripts/orchestration.py dispatch .local/task.json
```

For independent read-only lanes, use a verified batch. A minimal packet is:

```json
{
  "batch_id": "example-analysis",
  "sources": {"current": {"ref": "WORKTREE", "paths": ["go.mod"]}},
  "jobs": [
    {"key": "module", "kind": "explore", "bounded": true,
     "title": "Identify module declaration", "body": "Read supplied go.mod and report the module path.", "inputs": ["current"]},
    {"key": "toolchain", "kind": "review",
     "title": "Inspect toolchain requirements", "body": "Read supplied go.mod and report explicit toolchain constraints.", "inputs": ["current"]}
  ]
}
```

```powershell
python .agents/scripts/orchestration.py batch .local/batch.json
python .agents/scripts/orchestration.py batch-status example-analysis
python .agents/scripts/orchestration.py gc -- session list --json
python .agents/scripts/orchestration.py gc -- bd show TASK-ID --json
python .agents/scripts/orchestration.py stop
```

Batches select explicit aliases and regular file paths from WORKTREE, HEAD or a
full commit SHA. Inputs are limited to 512 files, 8 MiB each and 64 MiB total;
credentials, Git storage and generated host context are excluded. Bytes and a
manifest are verified on Windows and in the Linux reader namespace. Worktree
read races, aliases, links, corrupt copies and namespace changes block dispatch.
All 2..23 independent tasks are created before routing; all ready tasks are
routed before monitoring. Persistent IDs and task hashes allow resuming the same
packet after an uncertain create/sling outcome without duplicating jobs.
Never regenerate an ID to hide an unknown mutation outcome.

Workers save result comments using `status: DONE`, `status: NEEDS_CONTEXT` or
`status: UNRESOLVED_TECHNICAL`, including locations, facts, inference and missing
inputs, then follow native drain. A closed task alone does not prove success:
`batch-status` requires a saved DONE result. Native status can be cached or partial;
inspect exact task/session IDs and comments. A timeout is an unknown outcome;
reconcile before retrying. The general `gc -- ...` passthrough retains native
sessions, rigs, queues, Beads and Dolt functionality and is not a replacement
scheduler. Native commands remain real mutations and require their normal task
authority. `stop` releases this adapter's owned keepalive only after native stop
succeeds; it does not delete stores, worktrees or history.

## Validation boundary and recovery

Synthetic unit tests run without WSL or model credentials. They verify config
preservation, explicit routing/single deep pool, batch byte fidelity and replay,
worker alias rejection and reviewed hook fingerprints. An optional installed
gopls test runs only when gopls is on PATH or `XRAY_TEST_GOPLS` is set.

```powershell
python -m unittest discover -s .agents/scripts -p test_orchestration.py
python -m unittest discover -s .agents/scripts -p test_agent_batch.py
python -m unittest discover -s .agents/scripts -p test_model_router.py
python -m unittest discover -s .agents/scripts -p test_worker_context.py
python -m unittest discover -s .agents/scripts -p test_runtime_hooks.py
```

No external Luna/Sol/Astra execution, WSL provisioning, real queued model run or
end-to-end product/runtime acceptance is established by these tests. First-run
qualification must separately record exact runtime versions, hashes, source SHA,
context/catalog admission, task/session IDs, verified model/effort, result comments,
resource use and clean stop. Retain `.local/workspace` wave/batch receipts when
recovering interrupted work. Inspect `preparing-wave.json` and the native issue
before resuming a preparation. Preserve live or unrelated queues and worktrees;
this kit provides no automatic destructive cleanup or publication step.

Pinned implementation references: [GC init](https://github.com/gastownhall/gascity/blob/v1.5.0/cmd/gc/cmd_init.go),
[GC rig commands](https://github.com/gastownhall/gascity/blob/v1.5.0/cmd/gc/cmd_rig.go),
[GC hook rendering](https://github.com/gastownhall/gascity/blob/v1.5.0/internal/hooks/hooks.go),
[Codex hook discovery](https://github.com/openai/codex/blob/rust-v0.162.0-alpha.2/codex-rs/hooks/src/engine/discovery.rs)
and [native identity hashing](https://github.com/openai/codex/blob/rust-v0.162.0-alpha.2/codex-rs/config/src/fingerprint.rs).
