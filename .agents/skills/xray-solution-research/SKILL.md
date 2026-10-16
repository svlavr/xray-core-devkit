---
name: xray-solution-research
description: Find and compare practical implementations before adding or redesigning a Core capability. Use for uncertain mechanisms, integrations or proposed abstractions in new and existing code.
---

# Research a working solution

Start with the observable outcome and the decision that needs evidence. Read the
relevant native path and the human-supplied task/contract under
`docs/PROJECT_SCOPE.md`. Check assumptions in requirements as
well as assumptions in implementations; an existing document is not empirical
proof. Clear, familiar changes need a focused lookup, not a research ceremony.

Investigate the approaches that could materially change the choice: an existing
native API/configuration, a small direct implementation, and applicable external
implementations or components. A dependency is not automatically simpler than
native code. Inspect real source and its tests, not repository descriptions.
Use gopls for local Go semantics, GitHub/web and grep_app for public examples,
and Context7 for current public API documentation. Public search queries contain
public identifiers, never private code, contracts or subscription material.

Independent questions can run concurrently: native capability, external
implementation, and consumer/validation feasibility. Main dispatches useful
ready lanes under xray-orchestration; workers never create nested teams. Do not
multiply identical searches or split one coupled mechanism merely to fill slots.

For each serious candidate establish the actual input, mechanism, output and
consumer; version/ref, license, dependencies and constraints; what can be reused
directly; and the code or behavior still needed here. Explain why rejected
machinery is unnecessary. Prefer a concrete complete solution over a generic
registry, facade, adapter stack or hypothetical recovery system.

When a technical uncertainty can invalidate the choice, specify the smallest
real experiment and its deciding observation. Main assigns an authorized worker
and exact scratch/write set to execute it. A feasibility report is not an
executed experiment; a fixture does not prove a product or device path. Reuse
matching evidence. Resolve uncertainty during this task instead of leaving an
already requested capability as a future optional installation or phase.

Return a short decision for the implementer: chosen approach and supporting
sources, justified alternatives, full requested behavior and any evidence-based
revisions, the real integration path, remaining uncertainty and its next action.
Revise unjustified requirements openly; do not silently omit an inconvenient
outcome. Ask the human only for a material unresolved product/authority choice.
Stop collecting sources when additional evidence is unlikely to change the
decision. Do not edit runtime, accept a new architecture or publish from research.

The public workflow and adaptation boundary are in
`docs/WORKFLOW.md#practical-solution-research-and-complete-delivery`.
Research supplies evidence and recommendations; the human-selected project scope
and publication policy remain authoritative.
