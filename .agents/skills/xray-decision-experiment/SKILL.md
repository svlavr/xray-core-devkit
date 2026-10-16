---
name: xray-decision-experiment
description: Turn a material design or causal uncertainty into an actual bounded experiment with controls, owned execution and feedback. Use when an observation can decide between viable mechanisms or hypotheses.
---

# Execute a deciding experiment

Follow the human-selected scope in `docs/PROJECT_SCOPE.md` and
`docs/WORKFLOW.md#invention-criticism-and-experiments`. Name the unresolved
question and alternatives, not a desired winner. Reuse exact matching evidence;
a clear direct change needs no experiment ceremony.

`mu_test_architect` designs the observation independently of implementation:
input and real consumer, candidate/control, expected confirming and falsifying
results, root/base/build/tool identities, commands, resource limits, owned
scratch paths, artifacts and validation executor. Include a known-broken case
that the evaluator must reject. A green build, mock-only caller or a score
without evaluator validity does not decide consumer correctness.

Main assigns the existing `mu_go_worker` explicit **experimenter mode** with
that packet and an exact write set. Experiments are actual execution work:
implement only necessary candidate/control fixtures, run the approved commands
through `resource_guard.py`, retain successful and failed outputs, and return
artifact identities, observations and limits. No new experimenter profile,
scheduler or execution service is needed. A read-only researcher returns a plan;
it cannot claim the experiment ran. Parent permissions still govern tools.

Use isolated candidates or one owner for shared state, and serialize heavy
caches. Test evaluator failure handling, non-finite metrics where applicable,
wrong-root/stale receipts and absence of generated improvement. Missing input,
cancellation or failed selection remains unknown/failed, never fallback success.
Repeat or use held-out variants when variance could change the decision; do not
impose a fixed number of runs or discard failed attempts.

Main adjudicates actual observations against the original outcome, asks factual
researchers about unresolved source claims, and returns results to the innovator
and independent design critic. Revise the candidate or requirement on concrete
evidence with reasons; resolve material human choices without silently reducing
scope. Continue the chosen result through `xray-feature-delivery`, independent
real-consumer checks and applicable stable implementation review. A scratch
fixture proves only its measured boundary, not product/device/release readiness.

Native execution uses `mu_go_worker`; external packets use `kind=implement`
and identify experimenter mode in their body. Advisory acceptance/criticism uses
`kind=review` with its named competency. Existing model routing, no nesting,
capacity limits and explicit publication authority remain unchanged.
