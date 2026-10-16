# Xray Core DevKit

[Documentation](docs/README.md) · [Installation](docs/INSTALLATION.md) ·
[File map](docs/FILES.md) ·
[Download ZIP](https://github.com/svlavr/xray-core-devkit/archive/refs/heads/main.zip)

The complete configured Codex toolkit we use for Xray-core development: eighteen
skills, nineteen specialized agent roles, Go code intelligence, MCP process control,
source accounting, review, Android artifact qualification, guarded source exports
and Gas City orchestration.

This independent distribution shares the tools and engineering method. It
contains no Xray runtime, product plans, private source history, credentials or
personal account state. Downloading it does not connect any existing project.
You choose the exact source checkout when installing it.

## Start here

You need a Windows host with Python 3.11+, Git, Go, Node with npm, and a Codex CLI
that supports the supplied settings and roles. The recorded reference toolchain
is Go 1.27.0 and Node 24.18.0; dependency versions and platform limits are in
[installation](docs/INSTALLATION.md). Bring your own Codex authentication and
model access. The separate Linux/WSL external-worker runtime is included and
configured through [orchestration](docs/ORCHESTRATION.md).

There are two directories: the **DevKit root** contains `devkit.py`; the **source
root** is your chosen Git checkout of `github.com/xtls/xray-core`, or a fork that
retains that Go module path. Examples use `D:/Work/Xray-core` for the source and
`D:/Tools/xray-analysis` for dependencies. Substitute your own canonical paths.

Clone the toolkit, or extract the ZIP and open its `xray-core-devkit` directory:

```powershell
git clone https://github.com/svlavr/xray-core-devkit.git
```

```powershell
cd xray-core-devkit
```

From the DevKit root, verify the download, preview the copy and install:

```powershell
python devkit.py verify
```

```powershell
python devkit.py install --target D:/Work/Xray-core --dry-run
```

```powershell
python devkit.py install --target D:/Work/Xray-core
```

Then change to the selected source root:

```powershell
cd D:/Work/Xray-core
```

Install the locked analysis dependencies, generate local settings, inspect
startup and open a fresh Codex session:

```powershell
python .agents/scripts/dependencies.py install --tools D:/Tools/xray-analysis
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

If you already have the matching dependency layout, use `dependencies.py status
--tools D:/Tools/xray-analysis` before reusing it. Read the
[complete installation guide](docs/INSTALLATION.md) for prerequisites, conflicts,
updates and troubleshooting. Startup reports facts; the human still supplies
source task, behavior contract, baseline, write set and Git policy.

## What is configured

- **Skills and roles:** startup, research, Go analysis, implementation,
  orchestration, review, threat modeling, Android qualification, checkpoint,
  public CI and handoff. [All eighteen skills and nineteen roles](docs/README.md#skills-and-roles)
  remain available.
- **Complete delivery:** compare practical implementations, carry justified
  behavior through its real consumer, and review behavior and simplicity.
  Requirements can change on evidence; unfinished agreed work stays visible.
  [Delivery workflow](docs/WORKFLOW.md#practical-solution-research-and-complete-delivery)
- **Design and experiments:** complete alternatives, independent design criticism,
  factual research, acceptance design and actual owned experiments feed back
  into implementation and real-consumer checks. Workflow evaluation uses
  executable outcomes and evaluator controls, without forced novelty or quotas.
  [Invention, criticism and experiments](docs/WORKFLOW.md#invention-criticism-and-experiments)
- **Runtime specialties:** selected protocol/peer interoperability, lifecycle and
  concurrency, reachable security, Go/OS/ABI qualification and measured performance
  feed real-consumer checks. Load only the implicated methods; no automatic full
  roster, build matrix or device proof.
  [Runtime and protocol specialists](docs/WORKFLOW.md#runtime-and-protocol-specialists)
- **Model routing:** Luna High for narrow exploration, Sol 6.1 High for ordinary
  roles, and one Astra High adviser for a named technical question unresolved by
  Sol. The primary model stays the user's choice. Native capacity is 23, subject
  to the actual session and host limits.
- **Context:** 872000 nominal tokens, 95% effective capacity and compaction at
  80% of effective capacity, scope `total`. Local catalog checks do not grant
  account access or prove that an existing session adopted these settings.
- **MCP and analysis:** pinned gopls v0.23.0, GitNexus, Context7, grep.app public code search, Repomix when
  installed, ast-grep, package maps and deadcode. The Windows Go profile is
  enabled; Android Go is configured and initially disabled.
- **Process control:** owned descendant trees, isolated scratch, bounded I/O,
  deadlines, cancellation, idle backend eviction and initialization replay.
- **External orchestration:** Gas City, Beads, Dolt, verified input batches,
  source-pinned worker worktrees, explicit model routing and reviewed hooks.

Internal tasks and documentation use English; direct primary-coordinator
replies use Russian. Adapt that policy deliberately if needed. Agent
`sandbox_mode` fields express role intent; actual access comes from the parent
session's permissions. See [configuration](docs/CONFIGURATION.md) for exact
settings and their editable sources.

## Updates, checks and scope

Updates are deliberate file copies from a newly downloaded or pulled DevKit.
The installer records hashes, preserves local edits and leaves human text
outside its managed instruction blocks intact. Installed tools do not depend on
the DevKit download remaining available. Copying an update, regenerating local
settings and restarting a session are separate steps; follow the
[update procedure](docs/INSTALLATION.md#update-an-installed-checkout).

The distribution includes tooling regression tests for configuration, analysis,
MCP lifetime, orchestration, exports and installation. See
[maintenance](docs/MAINTENANCE.md#verify-a-change) for runnable contexts and skip
reporting. Xray runtime tests and private fixtures are outside this payload.
Source, host, device, network, performance and release evidence each require
their own proof; installing the toolkit transfers no historical acceptance.

Use the [documentation home](docs/README.md) to find the workflow, analysis,
accounting, export and orchestration guides. The toolkit does not authorize
source changes or publication merely by being installed.

## License

Toolkit source uses [MPL-2.0](LICENSE). Dependencies retain their own licenses;
the recorded GitNexus release has noncommercial terms. Read
[third-party notices](THIRD_PARTY_NOTICES.md) before using those components.
