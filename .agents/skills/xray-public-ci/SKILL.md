---
name: xray-public-ci
description: Prepare, verify and follow an explicitly authorized filtered Xray public source export and exact-source CI. Require a user-supplied export manifest; never publish private working HEAD or history directly.
---

# Filtered public source CI

Read the selected task/contract, `docs/PROJECT_SCOPE.md`, `docs/WORKFLOW.md` and
user-supplied `.agents/public-export.json`. The owner specifies exact source root,
committed SHA, public destination/ref, allowlist, ancestry policy and expected CI
jobs. Missing configuration or authority stops export; never infer them from
this toolkit's origin or use a private project's old manifest.

Use `.agents/scripts/public_export.py` to prepare, verify and, only when explicitly
authorized, publish the committed allowlist. Inspect its current CLI/manifest
schema. Require exact source/public file and blob correspondence and official or
public-only ancestry; exclude private instructions/development documents, host
state, credentials, raw evidence and private history. The runtime exporter always
protects toolkit, process and host directories, including `.agents`, `.codex` and
`.local`; an allowlist cannot override that protection. Distribute the toolkit
itself with `devkit.py package`. Never mirror or directly push a private working
branch. Preserve all other refs and defaults. No permanent second working copy.

Record source SHA, public SHA, manifest/hash and expected jobs. Run CI only on
the verified public tree, without private access. Follow each required check on
that exact SHA; configured workflow names and queued jobs do not prove execution.
Keep original fixtures, builds, ordinary OS tests, affected owner/fork race gates
and required checks. Fix causes in the authoritative source, then create and
verify a new export rather than patching the export as another source owner.

Apply `docs/WORKFLOW.md` fixture policy by actual conflicting access pair and
owning blobs/build. Retain every actual FAIL count and original attempt. A stock
baseline disposition does not qualify changed or corrected fork source. Missing,
running, skipped or cancelled is not PASS. Retry only a demonstrated transient
failure on the same SHA, preserving the original attempt and reason.

Report exact checks/results and source, device, network, performance and release
limits separately. No binary upload, release, PR, tag, visibility/default change,
private-history publication or process-only source CI follows implicitly.
