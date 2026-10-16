# Source accounting and guarded source export

These are complete local Git tools. They ship without a downstream ownership
catalog, adopted baseline, source receipt, public anchor or publication authority.
Examples under `.agents/metrics/examples/` are fictional configuration templates;
copying one does not constitute a review or make its synthetic object IDs real.

## Configure source accounting

Create `.agents/metrics/modules.json` with schema `1`, a nonempty `modules`
object, and an explicit `shared_fork_paths` list. Each named module has `paths`
and/or `prefixes` lists of repository-relative paths. Names are user defined;
`shared` is reserved. A file matching multiple modules blocks measurement. New
fork runtime files outside modules must be listed in `shared_fork_paths`.
Unchanged upstream runtime files naturally fall under shared accounting. A module
is an accounting owner, not an architectural or product acceptance assertion.

Choose and review an exact adopted upstream commit already present locally. The
tool never fetches a baseline or substitutes a project-specific default. Generate
and verify a snapshot using committed blobs or the exact staged index:

```powershell
python .agents/scripts/source_size.py snapshot --source INDEX --upstream <exact-commit> --catalog .agents/metrics/modules.json --output .agents/metrics/source-size.json
# Stage the reviewed catalog and generated snapshot with the owned change.
python .agents/scripts/source_size.py verify --source INDEX
python .agents/scripts/source_size.py verify --source HEAD
python .agents/scripts/source_size.py report --before before.json --after after.json
python .agents/scripts/source_size.py history --limit 20
```

`--repo`, `--catalog`, and `--snapshot` support explicit fixture/alternate inputs.
The snapshot records immutable file modes/blobs, physical line counts, per-file
upstream lengths, added/deleted/net lines, per-module and total summaries, source
and runtime fingerprints, the adopted upstream SHA and catalog digest. Runtime,
tests, generated Go, test support, docs, tools and other files remain separate.
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

The catalog may set `semantic_map`; its default is
`.agents/metrics/shared-integration.json`. `ownership_map.py --source HEAD` (or
`INDEX`) verifies that map after source-size verification. The JSON must contain
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
rejected. Unlisted non-private source files require an explicit manifest decision.
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
python .agents/scripts/public_export.py verify .local/export/<source-sha>.json
# Only after reviewing the concrete candidate and receipt:
python .agents/scripts/public_export.py publish .local/export/<source-sha>.json
```

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

`remote_evidence.py --remote <configured-name> --ref refs/heads/<branch>
--expected <optional-exact-sha> --output .local/evidence/new.json` performs a
bounded exact-ref observation. A fresh successful query is `LIVE`; failures or
malformed output are `UNAVAILABLE`, never local HEAD or a pinned substitute.
`reuse(prior, source)` yields `REUSED` with the original observation timestamp
and explicit evidence source. Receipts are create-only in ignored `.local/`;
failed observations and historical receipts stay available for audit.

## Offline validation

Run the unit modules `test_source_size`, `test_ownership_map`,
`test_public_export`, and `test_remote_evidence` from `.agents/scripts` through
the resource guard. Git fixtures create and remove only their own temporary
repositories; URL rewrite and publication tests are mocked or local. They do not
need any personal source history, baseline, GitHub credentials or real network
push. Host test results qualify these tools, not downstream runtime/device/network
behavior or release acceptance.
