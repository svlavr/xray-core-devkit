---
name: xray-fork-research
description: Evidence-first Xray Core research for fork divergence, upstream behavior, dependencies, licensing, security, core artifacts, and publication decisions. Use for requests to inspect examples, GitHub, or upstream behavior, or to decide whether upstream already solves a core requirement. Do not use for routine implementation of an accepted contract or a narrow local lookup.
---

# Bounded core research

Read `xray-core-start`, `docs/PROJECT_SCOPE.md`, the accepted task/contract and
exact baseline. Define one neutral
question and a bounded verdict: UPSTREAM_HAS_IT, FORK_GAP, PARTIAL, NOT_NEEDED,
DEFER or EXPERIMENT_REQUIRED. Current official source and accepted contracts
precede current fork evidence, matched experiments and external implementations.
This order establishes authority and the starting context, not empirical truth.
Test technical assumptions in requirements against actual code and observations;
revise unjustified assumptions with reasons within the authorized task. Use
`xray-solution-research` for practical implementation choices in new or existing
code. A routine repair does not require a new formal architecture document.

At the start of a substantial multi-owner review, split independent evidence
questions and dispatch them together with `xray-orchestration` before reading
every lane in main. Main owns synthesis and a separate useful lane while agents
work. Use the verified input batch for local files/pinned Git blobs; capture
public PR evidence once when shared by lanes. Do not defer all agents until
final review. A single tightly coupled question stays local with its reason.

Use exact refs/license/paths, keep known/disputed/unknown facts, and identify the
smallest discriminator. For a named shared Go owner/reference question apply
`xray-code-analysis`. Follow CODEX_PACK routing for independent evidence lanes.
Historical code supplies named counterexamples, never an inherited framework.
Do not copy GPL/proprietary/no-license implementations or resources into the core.
Verified evidence does not authorize implementation, deletion or publication.
Use `references/evidence-and-output.md` when a structured verdict is needed.
