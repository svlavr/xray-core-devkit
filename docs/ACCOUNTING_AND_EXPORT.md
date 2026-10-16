# Source accounting and guarded source export

This guide covers the Git tools installed in a selected Xray source checkout.
Run its commands from that source root after the owner supplies scope and
baseline under [project scope](PROJECT_SCOPE.md). Accounting reads local Git
objects; export preparation/publication has the separate network effects below.
For DevKit distribution checks and packaging, use
[maintenance](MAINTENANCE.md) from the root containing `devkit.py`.

The tools ship without a downstream ownership catalog, adopted baseline, source
receipt, public anchor or publication authority.
The [owner catalog example](../.agents/metrics/examples/modules.example.json)
and [export example](../.agents/metrics/examples/public-export.example.json)
are fictional configuration templates. Copying one does not constitute a review
or make its synthetic object IDs real.

## Configure source accounting

Create `.agents/metrics/modules.json` with schema `1`, a nonempty `modules`
object, and an explicit `shared_fork_paths` list. Each named module has `paths`
and/or `prefixes` lists of repository-relative paths. Names are user defined;
`shared` is reserved. A file matching multiple modules blocks measurement. New
fork runtime files outside modules must be listed in `shared_fork_paths`.
Unchanged upstream runtime files naturally fall under shared accounting. A module
is an accounting owner, not an architectural or product acceptance assertion.
Use trailing `/` in directory prefixes: matching is a literal string-prefix
test. Review overlaps across all named modules before measurement.

Choose and review an exact adopted upstream commit already present locally. The
tool never fetches a baseline or substitutes a project-specific default. The
workspace setup's comparison selection does not prove official adoption.

For an already initialized project, retain a before snapshot from committed HEAD
before editing. At an authorized checkpoint, first stage only the reviewed owned
change and catalog. Then generate the new snapshot from that index. The commands
below are a template: replace the quoted SHA placeholder with the full adopted
commit, and stage the generated snapshot before the index verification.

```powershell
$adoptedUpstream = '<full-adopted-upstream-commit-SHA>'
python .agents/scripts/source_size.py snapshot --source INDEX --upstream $adoptedUpstream --output .agents/metrics/source-size.json
# Main stages .agents/metrics/source-size.json with the exact reviewed owned set.
python .agents/scripts/source_size.py verify --source INDEX
```

Inspect the exact index, including catalog and snapshot, before the authorized
commit. After that commit, verify its HEAD separately:

```powershell
python .agents/scripts/source_size.py verify --source HEAD
python .agents/scripts/source_size.py history --limit 20
```

For first initialization, the catalog must be staged before measuring INDEX;
stage the resulting snapshot in the same commit. Neither file is supplied by
setup. Verification reads catalog/snapshot blobs from the selected Git tree or
index, so generating a worktree JSON file alone does not update the evidence.
Keep before/after comparison JSON outside scratch, for example in ignored
`.local/evidence/`, and run
`python .agents/scripts/source_size.py report --before .local/evidence/before.json --after .local/evidence/after.json`
after both files exist. Create output parent directories before invoking the counter.

`--repo` selects an explicit Git root. `--catalog` reads a supplied filesystem
catalog instead of its selected-source blob; `verify --snapshot` similarly reads
an alternate receipt. These are useful for explicit comparisons and fixtures,
but they do not establish that HEAD/INDEX contains those files. Normal checkpoint
verification above uses the staged/committed catalog and receipt without overrides.
The snapshot records immutable file modes/blobs, physical line counts, per-file
upstream lengths, added/deleted/net lines, per-module and total summaries, source
and runtime fingerprints, the adopted upstream SHA and catalog digest. Runtime,
tests, generated Go, test support, docs, tools and other files remain separate.
The category keys are `runtime`, `tests`, `generated`, `test_support`, `docs`,
`tooling` and `other`. Generated Go currently means `*.pb.go`; Go tests mean
`*_test.go`, and `testing/` is test support. This path-based classification is a
measurement convention, not automatic semantic ownership inference.
Binary non-runtime totals are marked partial. Binary runtime and unresolved index
entries fail. Intent-to-add, unstaged and untracked files do not become staged
source evidence. Concurrent source/index/metadata changes invalidate validation.

`.agents/metrics/` is excluded from the source fingerprint and line inventory to
avoid self-referential receipts; catalog changes remain visible through its digest.
Ignored host state and attachments are excluded. HEAD startup verification returns
`UNINITIALIZED` if neither catalog nor snapshot exists. Partial initialization,
stale snapshots and unmapped owners block verification. Pending index/worktree and
untracked candidates are reported separately from verified committed source.

## Review shared runtime necessity

When the source owner's task requires a shared-runtime necessity map, the catalog
may set `semantic_map`; its default path is
`.agents/metrics/shared-integration.json`. This is a separate validation tool;
source-size verification alone does not check the map:

```powershell
python .agents/scripts/ownership_map.py --source INDEX
python .agents/scripts/ownership_map.py --source HEAD
```

Use INDEX after staging the map and HEAD after the authorized commit. Each
invocation verifies source-size accounting first. The map JSON must contain
`upstream_sha`, `runtime_fingerprint` and a `files` list with exactly the changed
shared runtime files. Each record repeats the exact `path`, `blob`, `lines`,
`upstream_lines`, `added`, `deleted`, `net` facts and supplies nonempty `consumers`,
`blocks`, `necessity`, `removal_hazard`, `primary_module`, and `module_relations`.
Semantic module names must come from the catalog or the reserved `native` owner.
Missing, duplicate, stale or incomplete evidence fails. This checks recorded
review evidence; it does not automatically infer call graphs or prove necessity.

## Configure a filtered public export

Commit an explicitly reviewed `.agents/public-export.json`. Required fields are:

- `schema: 1`, `public_anchor`: an exact locally available clean public commit.
- `public_url`: an explicit HTTPS repository URL ending in `.git`.
- `public_ref` and `anchor_ref`: exact `refs/heads/...` branch refs.
- `paths`: the complete nonempty allowlist of public files in the source commit.
- `ci_blobs`: an object pinning every `.github/workflows/` file to its exact blob.
- Optional `historical_only`: retired public paths mapped to lists of exact
  `{ "mode": "100644", "blob": "<exact-blob>" }` versions admitted only in history.

The anchor is a user-reviewed trust boundary. The tool verifies the linear public
history after it, rejects private source ancestry/merges and forbids unknown paths
or modes. Review the anchor and its prior history independently before adopting
it. `historical_only` never admits a retired file into a new export. The selected
current tree must match every allowed source blob exactly. Symlinks, submodules,
path traversal, case aliases and protected tool/private/host/environment paths are
rejected. Every non-protected source path must be allowlisted; merely omitting
an ordinary path makes preparation fail. The runtime exporter always protects
`.agents`, `.codex`, `.private`, `.local`, `.git`, attachment directories,
`AGENTS.md`, `AGENTS.override.md` and environment-file names. These are not a
way to publish the toolkit itself; use `devkit.py package` for that task.
This is a path/history/identity guard, not a secret scanner: review allowed content.

The user-owned `.agents/project.json` (or ignored workspace context) must set
`public_push_mode` to `filtered-export-only`. There is no automatic publication
permission. Worker checkouts are rejected before export preparation or publication,
including when they inherit the tracked manifest and enabled project policy: either
a local `worker` context flag or `.local/workspace/worker.json` marker blocks them.
Optional project policy `public_url`, `public_branch` and `anchor`
must agree with the committed manifest. Ordinary remote push policy remains the
workspace guard's responsibility; the exporter pushes only the validated explicit
public SHA to the explicit public ref. It does not push source HEAD or source
history. A repository must be clean and committed before prepare/publish.

```powershell
python .agents/scripts/public_export.py prepare --message "Reviewed public change"
```

`prepare` prints a `receipt` path. Use that exact returned file for the separate
verification, then publish only within the explicitly authorized task:

```powershell
$exportReceipt = '.local/export/<full-source-SHA>.json'
python .agents/scripts/public_export.py verify $exportReceipt
python .agents/scripts/public_export.py publish $exportReceipt
```

Replace the quoted receipt placeholder with the actual returned path. `verify`
checks candidate/source identity and history locally; it neither publishes nor
establishes a fresh remote observation. `publish` performs its own destination
and remote checks. This exporter does not start or follow hosted CI. Use
[xray-public-ci](../.agents/skills/xray-public-ci/SKILL.md) for the separately
selected checks, expected jobs and exact-public-SHA results.

`prepare` observes the configured public ref, checks the configured anchor ref
for first publication, and may fetch a missing public parent. It builds a separate
index and a public-only commit, leaving the source index and HEAD intact. Receipts
contain source/public identities, manifest digest, destination, expected remote,
tree and per-file provenance. `publish` revalidates committed source and receipt,
refuses remote movement, rejects URL rewrites, performs a non-force explicit SHA
push and observes the resulting remote SHA. Retrying an already published exact
candidate returns `ALREADY_PUBLISHED`. These commands can contact the network;
no such publication is needed to install, initialize or test the toolkit.

## Remote evidence

From the installed source root,
`python .agents/scripts/remote_evidence.py --remote origin --ref refs/heads/main --output .local/evidence/new.json`
performs a bounded exact-ref observation. A fresh successful query is `LIVE`; failures or
malformed output are `UNAVAILABLE`, never local HEAD or a pinned substitute.
`reuse(prior, source)` yields `REUSED` with the original observation timestamp
and explicit evidence source. Receipts are create-only in ignored `.local/`;
failed observations and historical receipts stay available for audit. Substitute
the actual configured remote name and full branch ref. Add `--expected` with the
full expected SHA when checking publication. This command contacts the network;
it does not fetch or grant push authority. `reuse` is a Python function, not a CLI
subcommand.

## Offline validation

The [maintenance guide](MAINTENANCE.md) gives the guarded test commands. Relevant
unit modules are `test_source_size`, `test_ownership_map`, `test_public_export`
and `test_remote_evidence`. Git fixtures create and remove only their own temporary
repositories; URL rewrite and publication tests are mocked or local. They do not
need any personal source history, baseline, GitHub credentials or real network
push. Host test results qualify these tools, not downstream runtime/device/network
behavior or release acceptance.
