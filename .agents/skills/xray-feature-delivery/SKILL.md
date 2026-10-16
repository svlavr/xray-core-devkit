---
name: xray-feature-delivery
description: Deliver a new or changed Core capability through its real consumer, from solution research to integrated verification. Use when the mechanism or behavior must be developed, not just inspected.
---

# Deliver the requested behavior

Apply `xray-fork-implement` and the human-supplied task authority in
`docs/PROJECT_SCOPE.md`. Establish the requested
outcomes and actual consumer before selecting machinery. Keep a concise account
of what is delivered, revised with reasons, or blocked; use the existing task
record rather than inventing a ledger for every edit. Requirements are testable
assumptions and can be revised on evidence. Explain material changes, obtain a
human decision where product/authority choices remain unresolved, and preserve
the requested goal. Never turn unfinished agreed work into optional future work
to declare completion.

Use xray-solution-research when the approach, integration or proposed abstraction
is uncertain. For a clear direct change, proceed without a mandatory design
document. Choose the least machinery that implements the whole justified scope.
A small implementation is useful only if it serves the actual required behavior.

Main computes the ready frontier under xray-orchestration. Independent native and
external research, consumer/test design, disjoint owners and applicable reviews
run in parallel within observed capacity and leases. Profiles are competencies,
not a fixed team size. Implementations that share state or files have one owner
or isolated worker branches; dependent work starts when its input is ready.

Implement complete paths from a real input to the result consumed by callers.
Order work as executable behavior; scaffolding belongs inside such a task.
Intermediate slices and spikes help execution but do not reduce the agreed final
scope or end this task early. Resolve missing tools/integration as part of the
authorized task when possible. Keep actual external blockers explicit and
continue independent work; never label blocked behavior successful.

Use direct native behavior before adding wrappers. Add validation, fallback,
retry, abstraction or extensibility for a concrete requirement or reachable
failure, not hypothetical future consumers. Preserve real errors, cancellation,
resource ownership and ordinary native behavior. A missing implementation returns
an honest failure; it must not become a placeholder success or a fake fallback.

Before closing, main assigns independent consumer-behavior and simplicity review
where each adds material value. Behavior review traces input through selected
runtime wiring to the consumer and checks expected results and relevant failures.
Tests must detect a meaningful broken behavior; mocks, build success, coverage
and file presence alone cannot prove integration. Simplicity review challenges
redundant layers and speculative defenses while preserving required behavior;
it does not optimize LOC or invent new requirements. Existing correctness,
performance and critical reviewers remain applicable to their actual risks.

Repair findings, finish all still-required outcomes, validate integrated bytes,
then apply `xray-fork-checkpoint` only within the human's explicit task or saved
policy for the exact repository/ref. This distribution grants no default commit
or push authorization. Report what was executed, what changed
on evidence and any real limitation. Source/host, artifact, device, network and
release results retain their actual boundaries.

The public workflow and adaptation boundary are in
`docs/WORKFLOW.md#practical-solution-research-and-complete-delivery`.
