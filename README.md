# Xray Core DevKit

The complete configured Codex toolkit we use for Xray-core development: skills,
specialized agents, Go code intelligence, MCP lifecycle control, source accounting,
review, Android artifact qualification, guarded source exports and external
Gas City orchestration.

This is an independent project that shares the tooling and engineering method.
It contains no Xray runtime implementation, product development plans, research
receipts, personal account state or private source history. Downloading it does
not attach it to any existing project. Installation and updates operate only on
the explicit target supplied by the user.

## Complete working configuration

- **11 skills:** startup, research, code analysis, implementation, orchestration,
  adversarial review, threat modeling, Android validation, checkpoints, public CI
  and handoff.
- **8 roles:** explorer, investigator, upstream researcher, Go worker, reviewer,
  performance reviewer, critical reviewer and a deep reviewer for one evidenced
  unresolved technical question.
- **Model policy:** Luna High for narrow exploration, Sol 6.1 High for ordinary
  work, Astra High for the named deep discriminator. The primary model remains
  the user's choice. Configured native worker capacity is 23, subject to the
  actual session and host limits.
- **Context policy:** 872000 nominal tokens, 95% effective context, compaction at
  80% of effective capacity, scope `total`. Local model capabilities are checked
  when available; settings do not grant account access or prove session adoption.
- **MCP:** pinned gopls, GitNexus, sandboxed Repomix and Context7. Windows Go is
  enabled; Android Go is configured but initially disabled, as in the working
  setup. Repomix is enabled when installed. Analysis helpers include ast-grep,
  package-import maps and deadcode.
- **External orchestration:** Gas City, Beads, Dolt, exact input batches,
  source-pinned worker worktrees, controlled model routing and reviewed hooks.
- **Process control:** owned descendants, isolated scratch, bounded I/O and
  deadlines, idle backend eviction, initialization replay and cancellation.

The language setting keeps internal tasks, reports and documentation in English,
with Russian direct replies from the primary coordinator. Keep it or deliberately
adapt it for your own work. Agent role instructions do not create a separate OS
sandbox; the parent session supplies actual permissions.

## Install in your own Xray checkout

See [installation](docs/INSTALLATION.md) for requirements and complete commands.
The toolkit targets the `github.com/xtls/xray-core` Go module, including forks that
retain that module path. It shares the current Windows/Linux tool arrangement;
macOS process supervision and other clients are not qualified by this project.

From this downloaded repository:

```powershell
python devkit.py verify
python devkit.py install --target D:/Work/Xray-core --dry-run
python devkit.py install --target D:/Work/Xray-core
```

Then from the selected Xray checkout:

```powershell
python .agents/scripts/dependencies.py install --tools D:/Tools/xray-analysis
python .agents/scripts/workspace.py setup --analysis-tools D:/Tools/xray-analysis
python .agents/scripts/check_core.py
python .agents/scripts/session.py --
```

If the complete dependency set is already installed in that layout, inspect it
with `dependencies.py status --tools ...` and reuse it. Tools are installed into
the selected directory; authentication is supplied independently by the user.
Context7 needs network access; the external runtime needs the user's own Linux
environment, city, local queue and Codex login. No credentials are supplied.

## Updates and file-linked instructions

Skills intentionally use separately maintained reference files, scripts and
configuration. Those files are included in the distribution. Download or pull a
new reviewed copy of this repository, then run:

```powershell
python devkit.py update --target D:/Work/Xray-core --dry-run
python devkit.py update --target D:/Work/Xray-core
```

Updates copy files; installed projects do not depend on the development checkout
remaining available. The installer records hashes and refuses to overwrite local
edits or conflicting files. Human instructions outside its managed blocks remain
intact. Host settings and account state are never part of the update payload.
After accepting an update, rerun workspace setup and start a fresh session when
configuration, roles or MCP launchers changed.

## Documentation

- [Project scope and authority](docs/PROJECT_SCOPE.md)
- [Workflow, evidence and validation](docs/WORKFLOW.md)
- [Checkout configuration](docs/CONFIGURATION.md)
- [Go and MCP analysis](docs/ANALYSIS.md)
- [Accounting and source export](docs/ACCOUNTING_AND_EXPORT.md)
- [External orchestration](docs/ORCHESTRATION.md)
- [Maintenance and distribution checks](docs/MAINTENANCE.md)
- [Third-party components](THIRD_PARTY_NOTICES.md)

The skills apply the user's task and source contracts; they do not invent a
product architecture or authorize publication. Source, host, device, network,
performance and release evidence remain separate.

## License

Toolkit source is distributed under the included [MPL-2.0](LICENSE).
Third-party tools retain their own licenses. In particular, the recorded
GitNexus release has noncommercial terms; see the component notices. The
distribution does not relicense those dependencies.
