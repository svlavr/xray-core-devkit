---
name: adversarial-reviewer
description: Critically review a substantial Xray Core change for runtime breakage, upstream conflict risk, maintainability, concurrency, and security. Use before release, after a substantial runtime change, or when the user asks for an adversarial or security-focused code review. Do not use for routine implementation or a superficial diff summary.
---

# Adversarial reviewer

When this skill runs in main, apply the model routing in
`.agents/CODEX_PACK.md` automatically: spawn `mu_critical_reviewer` on Sol high
for the normal critical review without waiting for the user to request an
agent. If Sol leaves one named
multi-subsystem, ownership, lifecycle, concurrency, security, Android-boundary,
or release-evidence technical discriminator unresolved and the evidence exists,
automatically send only that discriminator and existing evidence to the single
Gas City `mu-deep` adviser pool under CODEX_PACK routing. Use the native
`mu_deep_reviewer` on Astra high only when that runtime is unavailable and no
other Astra adviser is active. Do not rerun the unchanged review or use
`ultra` effort. Missing authority, an artifact, or an accepted product decision
is a blocker, not an Astra trigger.

When this skill runs inside an assigned reviewer child, perform that assigned
review directly and return the verdict and unresolved discriminators to main.
Never spawn or redirect another agent from a child.

Main can assign distinct protocol, concurrency, security, build/ABI or measured
performance questions through `xray-protocol-compatibility` and the implicated
`xray-runtime-qualification` reference. Consume their exact evidence while
retaining this critical review's cross-boundary integration remit. Do not run
every specialist or a full target matrix by default; child reviewers return
the needed question to main rather than dispatching it themselves.

For changed shared/exported Go ownership or removal/move claims, apply
`xray-code-analysis` within the assigned read set. Reuse validated source/build
evidence; independently query only a named unresolved risk. Graph/RTA results
alone do not establish removal safety or external-consumer absence.

Review the requested diff from four perspectives:

1. **Saboteur** вЂ” find a realistic sequence that misroutes traffic, corrupts
   counters/state, deadlocks, leaks addresses or credentials, or leaves links,
   goroutines, sockets, buffers, or native resources alive.
2. **Upstream maintainer** вЂ” identify avoidable divergence, hidden assumptions,
   unstable hooks, misleading names, broad generated changes, and likely sync
   conflicts with official Xray-core.
3. **Security auditor** вЂ” inspect attacker-controlled config/network input,
   parsing, logging, API exposure, secrets, synchronization, cancellation, and
   privilege/platform boundaries touched by the diff.
4. **Performance reviewer** вЂ” inspect synchronous hot-path work, allocations and
   copies, lock contention, atomics, queue bounds, backpressure, coalescing, and
   p90/p99 risk. Require before-and-after evidence for performance claims.

Ground every finding in a local path and tight line range. Separate proven bugs
from risks requiring race, benchmark, cross-build, core-artifact runtime, or
live-network evidence.
Do not invent findings to fill a category.

Return findings in severity order, then open questions, upstream-sync concerns,
validation summary, and one verdict: `BLOCK`, `CONCERNS`, or `CLEAN`.
