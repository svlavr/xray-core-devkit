# Maintain the independent toolkit

Edit the public toolkit in this repository. Its presence does not configure or
modify any other project. Installed users deliberately accept updates through
`devkit.py`; there is no global symlink, automatic cross-project synchronization
or hidden source-checkout dependency.

Keep all 11 skills, 8 roles and complete tool workflows unless the human selects
a change. Update file-linked instructions and implementations together. New
tools or abstractions need a concrete task rather than a target feature count.
Keep configuration intent, successful invocation and confirmed results distinct.

## Verify a change

```powershell
python .agents/scripts/resource_guard.py --timeout 180 -- python -m unittest discover -s tests -v
python .agents/scripts/resource_guard.py --timeout 300 -- python -m unittest discover -s .agents/scripts -p "test_*.py" -v
python .agents/scripts/workspace.py validate
```

The analysis regression modules need a checkout-local ignored test context;
use a configured installed synthetic/source checkout when running those modules.
They do not need private project contracts. Real gopls tests use a supplied
`XRAY_TEST_GOPLS` path or the executable on PATH, and report a skip if absent.
Never conceal skips as runtime qualification. External-runtime unit fixtures do
not prove an authenticated Gas City model run. Run only the necessary checks and
reuse exact matching receipts; preserve actual failures.

Review nontrivial changes independently after their bytes stabilize. In
particular, process termination, scratch recovery, cancellation, source export
and installation/update paths require failure-path review. Maintain upstream
tool versions and licenses together; a changed gopls version requires review of
its version-specific location correction, not only a new lock value.

## Review public contents and package

Review the exact changed tree and then refresh its public file manifest:

```powershell
python devkit.py manifest
python devkit.py verify
python audit.py
python devkit.py package --output .local/dist/xray-core-devkit.zip
```

The manifest intentionally includes only toolkit source/settings/docs/tests and
dependency metadata. It excludes Git history, `.local`, account files, caches,
build outputs and user-supplied source catalogs/export policies. Examples use
synthetic projects. Neither hash integrity nor the generic audit replaces review
for source code, prose or identifiers copied from a private project.

Keep actual source-project receipts and extraction evidence outside the public
tree. Never add application code, customer data, project research, captured
traffic, subscriptions or personal authentication to explain a tooling change.
Use small synthetic fixtures and public upstream references instead.

This repository has independent Git history. A local toolkit commit does not
authorize a remote repository, tag, release, PR or binary publication. Public
GitHub creation/publication is an explicit owner operation on the reviewed tree.
