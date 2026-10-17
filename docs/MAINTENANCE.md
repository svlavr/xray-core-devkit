# Maintain the independent toolkit

Edit the public toolkit in this repository. Installed users deliberately accept
copies through `devkit.py`; the distribution does not synchronize existing
projects automatically. Keep all eighteen skills, nineteen roles and their linked
references unless the human selects a change. See the [file map](FILES.md) for
ownership and [configuration](CONFIGURATION.md) for maintained settings sources.

Update instructions and implementations together. A new tool or abstraction
needs a concrete use case. Preserve the distinction between configured intent,
successful invocation and confirmed results. Review stable nontrivial changes
independently, especially process lifetime, cancellation, scratch recovery,
installation/update and source-export failure paths.

## Verify a change

There are two test contexts. The DevKit root has distribution tests and static
policy validation. Some analysis tests import checkout-local host context, so
the full script suite needs a configured installed source or disposable fixture.
Do not run source startup/setup in the DevKit root: this repository has no Xray
Go module.

### Distribution checks in the DevKit root

With Python 3.11+ and Git available, run:

```powershell
python .agents/scripts/resource_guard.py --timeout 180 -- python -m unittest discover -s tests -v
```

```powershell
python .agents/scripts/workspace.py validate
```

The first command exercises install/update, packaging and public-audit fixtures.
The second checks the eighteen skill entrypoints and nineteen role policies without
requiring source-host context. In installed checkouts, extra source-owned skills
and roles are reported separately and preserved. This is not `workspace.py
verify`, which checks an installed source checkout.

### Script tests in a configured disposable checkout

Use a separate disposable Git checkout or synthetic Xray-module fixture with a
named branch and initial commit. Install the exact candidate toolkit there and
configure its ignored context with `workspace.py setup`; follow
[installation](INSTALLATION.md). For edits not yet in the distribution manifest,
review the candidate files and regenerate the manifest before using the
installer, as described below. Updating an existing test fixture uses `update`,
not `install`.

For these tests, a synthetic fixture can contain only a `go.mod` declaring
`module github.com/xtls/xray-core` and its initial Git commit. Setup requires an
existing tools directory. Tests supply their own temporary source/protocol
fixtures; a successful run does not qualify the synthetic fixture as Xray.
The optional real gopls case additionally needs Go and pinned gopls `v0.23.0`.

From that configured disposable source root, select the real adapter binary if
it is installed outside PATH:

```powershell
$env:XRAY_TEST_GOPLS = 'D:/Tools/xray-analysis/bin/gopls.exe'
```

Then run the copied script suite:

```powershell
python .agents/scripts/resource_guard.py --timeout 300 -- python -m unittest discover -s .agents/scripts -p "test_*.py" -v
```

The adapter test falls back to `gopls` on PATH when `XRAY_TEST_GOPLS` is absent;
it reports a skip when no binary exists. Other platform-specific tests can skip
when the host lacks their required capabilities. Record test totals, exact
source bytes, host/tool versions, failures and skip reasons. Never present a
skip as runtime qualification. Tests against an older installed copy do not
validate the candidate being maintained.

Use focused modules for a bounded change and run the relevant regression set.
Run each check with one executor, serialize heavy caches, and reuse exact
matching receipts. Repeat after relevant edits, failures or unresolved concerns.
Keep durable output outside managed scratch and preserve actual failing attempts.
External-runtime unit fixtures do not prove an authenticated Gas City model run.

Xray runtime tests belong to the exact source revision and behavior contracts;
they are outside this tooling payload. Accumulated project-specific core tests
are not imported by this distribution. Tooling tests, source/host, Android,
network, performance and release acceptance remain separate.

## Selected-role regression scope

For execution/profile changes, run the focused `test_role_profiles`,
`test_session`, `test_role_bootstrap`, `test_agent_batch`, `test_model_router`,
`test_orchestration`, `test_runtime_hooks`, `test_worker_context`,
`test_workspace` and `test_agent_workflow` modules through resource_guard with
bounded durable logs. The catalog/session/bootstrap tests also run in the
standalone DevKit; fixture sources synthesize the required official module path
without running source setup in this root. Retain installed-source tests for
actual host-context-dependent adapters.

Verify managed-extra behavior in a disposable installed copy: preserve an
owner-created role, skill and instructions through install/update and validate;
list only the nineteen maintained profiles. Freeze public PROJECT_SCOPE and
WORKFLOW documents and explicit non-xray skill packages, not private project
authority. Test quoted/dotted overrides and Unicode paths, immutable resumes,
actual worker MCP root, city-versus-rig operations and invocation-only trust.
Cover bound resume without trigger environment, one-time retained legacy
identities, unchanged generic legacy argv/cwd and rejection of new/partial
unbound jobs. Preserve old records and closed results.
All-catalog construction/hash checks prove input availability and selection,
not execution of every model or every live role. Stubbed Codex/GC process tests
are identified as such. Final package/install/update and native config/root
checks must use the final exact extracted bytes; any authenticated model run is
a separate explicitly selected gate. No source checkpoint destination is supplied
by the DevKit; that policy remains user-owned.

## Review public contents and package

Review exact changed source, settings, docs and dependency licenses first.
Confirm that examples use synthetic/public inputs. Then, from the DevKit root,
refresh the allowlisted hashes:

```powershell
python devkit.py manifest
```

```powershell
python devkit.py verify
```

```powershell
python audit.py
```

`manifest` writes new hashes; it is a maintainer operation after content review,
not a way for users to bless a damaged download. `verify` compares current bytes
and paths with the manifest. The audit provides additional content checks, not a
substitute for review. If review or tests require another edit, refresh and
verify the manifest again before copying or packaging those bytes.

Create an archive using a new output path:

```powershell
python devkit.py package --output .local/dist/xray-core-devkit.zip
```

Packaging refuses to overwrite an existing archive. Select a new filename for
another attempt. The package contains the manifest allowlist and its manifest,
with no Git ancestry. The public allowlist includes toolkit source/settings,
docs, tests, examples and dependency metadata; it excludes host `.local/`
state, account files, caches, build output, and owner-created source catalogs
or export policies. Hash integrity does not prove content is suitable for public
disclosure.

For a distribution change, validate the actual clean extracted archive as well
as the source tree: verify its manifest/audit, install into an explicit disposable
target, test update/conflict handling as applicable, provision dependencies and
exercise the changed commands. Record downloaded versions and actual invocation
results. Do not substitute package metadata or a configured server entry for a
successful backend operation.

Maintain tool versions, locks and license notices together. A new gopls version
requires review of version-specific location normalization, rather than only a
lock edit. Keep source-project receipts, extraction evidence, raw logs, captures,
subscriptions and credentials outside the public tree. Use small synthetic
fixtures and public upstream references when explaining a tooling change.

This repository has independent Git history. A local toolkit commit does not
authorize a remote repository, PR, tag, release or binary publication. Public
GitHub creation/publication is an explicit owner operation on the reviewed tree.
