---
name: xray-fork-android-validation
description: Validate an accepted Android-targeted Xray Core artifact, including cross-build, binding symbols, native loading, ABI compatibility, lifecycle, and resource cleanup. Use only after an executable core artifact exists or when the user explicitly requests validation of that core artifact. Do not use for docs-only work, host-only Go changes, or downstream application behavior.
---

# Accepted Android artifact validation

Read `docs/PROJECT_SCOPE.md`, `docs/WORKFLOW.md`, the accepted task/contract,
current host context and exact source/build/artifact hashes.
Use only when a real accepted Android-targeted core artifact exists or the owner
explicitly requests its validation. Source-only/process work does not trigger it.

Check target ABI/API/toolchain/binding symbols and actual native loading; run
the agreed lifecycle/cancellation/custody/resource and packet tests on the
declared device/AVD and consumer. Preserve platform socket/protect/underlay
ownership and raw facts; no product caller or environment may be invented.
Keep host/source, cross-build, executable artifact, binding, AVD/physical device,
network, performance and release evidence distinct. Report exact commands,
hashes, caller/device/workload, results and unsupported/unverified boundaries.
