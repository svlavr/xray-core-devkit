---
name: xray-runtime-qualification
description: Qualify changed native runtime behavior using selected concurrency, security, build/ABI or measured performance methods. Use only the implicated mode and real consumer; no automatic full roster, target matrix or device/release proof.
---

# Qualify the changed runtime boundary

Start from `docs/PROJECT_SCOPE.md`, the accepted source/contract, actual consumer
and changed owners. Select only the mode needed and read its reference:

- [Concurrency and lifecycle](references/concurrency.md): admission/retirement,
  locks, atomics, callbacks, pools, shared carriers or blocked I/O;
  `mu_concurrency_reviewer` owns the resource/transition and wait-graph evidence.
- [Security](references/security.md): changed untrusted input, authentication,
  trust/identity/routing isolation, secrets, privilege or resource admission;
  `mu_security_reviewer` owns reachable input-to-sink and abuse-control evidence.
- [Build, OS and ABI](references/build.md): target/tag, toolchain/dependency,
  generated/assembly, native compatibility or artifact/binding questions;
  `mu_build_qualifier` owns the exact selected-source/target qualification map.
- [Measured performance](references/performance.md): optimization, contention,
  allocations, retention, throughput, load/backpressure or quantitative claims;
  the existing `mu_performance_reviewer` designs controlled measurements or
  independently reviews their results in explicitly assigned modes.

Protocol/configuration/wire questions use `xray-protocol-compatibility`.
Specialists supply distinct evidence, not competing runtime owners. Keep the
critical reviewer for genuine interactions across boundaries and release risks;
the behavior reviewer still checks actual consumer wiring. A single isolated
question can stay local; useful independent questions follow
`xray-orchestration` without a fixed roster or one-instance-per-role limit.

The test architect checks that the deciding assertions detect a meaningful
broken case and retain native countercontrols. Specialists normally assess
source/receipts or design scoped checks. Main assigns actual builds, tests,
profiles, fault injection and repairs to a worker with exact owned paths and
resource limits through `xray-decision-experiment`. Advisory external work uses
`kind=review` with the specialist instructions explicitly supplied; execution
uses `kind=implement`. A pool label does not prove a named native role ran.

Preserve failed attempts and distinguish race/logic/deadlock, exposure/impact,
compile/link/load, and cost/correctness claims. Missing facts remain unknown;
test success does not strengthen a native cancellation, delivery, trust or join
contract. Evidence may justify requirement revisions with reasons, without
silently omitting behavior. No blanket quotas, universal joins, speculative
hardening, automatic build matrix, new service or source/publication authority.
Parent permissions, main's selected model and capacity 23 remain unchanged.
