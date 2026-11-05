# Initial model selection

Main selects the competency and model from the task's owner, scope, inputs and
acceptance before launching a worker. The human need not choose a model for
each task. This is semantic coordinator selection, not a task-title classifier
or a sequence of retries through different models.

## Defaults and bounded alternatives

The maintained catalog stays at nineteen roles and eighteen skills. Default
roles use High: seventeen Sol 6.1 roles, one Luna explorer and one Astra adviser.
The parent model remains the human's choice. Native custom types retain these
declared defaults; alternate presets use the bound CLI or external route.

`.agents/orchestration/model-presets.json` defines five Terra 6.1 High initial
assignments on existing roles:

- `native-write-fix` / `mu_go_worker`, implement: an accepted existing writer
  repair with exact paths and explicit partial-write, error, accounting and
  custody acceptance through its actual consumer.
- `native-accounting-review` / `mu_reviewer`, review: a read-only writer change
  review against supplied accounting, receipt, error and ownership contracts.
- `delivery-evidence-review` / `mu_behavior_reviewer`, review: a bounded tooling
  or source/host receipt audit using actual call/result/root/generation evidence.
- `tool-update-evidence` / `mu_upstream_researcher`, review or explore: a scoped
  tool-version compatibility assessment from supplied source and execution
  evidence, preserving unknown or unexecuted boundaries.
- `existing-writer-solution` / `mu_solution_researcher`, review or explore: select
  an existing writer integration seam against supplied identity, buffering,
  accounting and unsupported-case requirements.

Read the full preset scope and acceptance before selecting it. These are narrow
assignments, not a promotion of the complete role to Terra or evidence of general
model superiority. Broader architecture, concurrency, security, protocol and
release questions retain Sol initially. Installation grants no source-change
authority or runtime/device acceptance. The human supplies the selected source,
behavior contract, write set, baseline and publication policy.

## Select and execute

A named preset requires its exact role, compatible kind, `bounded: true` and
no cross-owner scope. For example, after supplying the exact source/contract:

```json
{
  "kind": "review",
  "role": "mu_reviewer",
  "preset": "native-accounting-review",
  "bounded": true,
  "cross_owner": false,
  "title": "Review the assigned native writer accounting",
  "body": "Review only the supplied writer change and contract; report concrete triggers, effects, corrections and supported clean cases. Read-only."
}
```

Save the completed packet under `.local/`. From the configured source checkout:

```powershell
python .agents/scripts/session.py --role mu_reviewer --task .local/writer-review.json --exec --json "Read .local/writer-review.json and inspect only its assigned source and contract"
```

`--task` supplies routing metadata; the direct CLI prompt tells the worker which
assignment to execute. Do not assume the task body is automatically appended to
the direct prompt. External dispatch uses the same `preset` field and its normal
scoped `body`, source inputs and implementation-packet requirements:

```powershell
python .agents/scripts/orchestration.py dispatch .local/writer-review.json
```

The selected full role instructions remain in force. Preset scope and acceptance
are appended, with model, High effort, profile/policy/entry/selection hashes and
the selection request retained through frozen launch and resume. Do not replace
the verified adapter, root, skills, source or parent permissions to obtain a
cheaper model. Unknown or mismatched selections and arbitrary model/effort
overrides fail before model entry. A requested preset is an initial assignment,
not a way to retry an already attempted task on another model.

## Unresolved work and retained jobs

Luna or Terra returns a concrete unresolved scope/evidence boundary to main;
there is no automatic cheaper-model ladder. Missing files, account access,
environment or unrun validation require context, not a stronger model.
Only a named technical discriminator still unresolved after Sol, with prior Sol
evidence, can enter the single Astra High adviser. Select `mu_deep_reviewer`
explicitly and retain the existing discriminator/evidence gate. Do not repeat
an unchanged Astra inquiry; return ordinary implementation to its scoped owner.

New admission uses current policy. An existing exact saved single/batch packet
retains its frozen assignment, helper, source and result identities on recovery;
an update must not reinterpret it under today's preset policy. Preserve active
jobs and uncollected results. A modified packet is a new assignment, not recovery.

Native configuration/MCP checks, authenticated model runs, accepted task outcomes
and general model quality are separate evidence. Qualify concrete consumers and
meaningful invalid controls before expanding a preset's scope. All models retain
the configured context/compaction policy; model selection grants no additional
permissions or tools.

## Interrupted calls

`aborted before dispatch` is a native cancellation result before the selected
tool starts; it is not evidence that a project script, model route or MCP backend
failed. Distinguish it from a callable's actual error and retain original task
and result identities before retrying an operation with side effects.

Generated primary configurations set `features.defer_mailbox_preemption=true`
to preserve prepared calls across automatic agent-mail arrivals. Queued mail is
delivered at a normal boundary; human stop/steer remains separate. The flag is
UnderDevelopment and was qualified on Codex 0.166.0-alpha.6 with a controlled native
scripted-provider experiment, not real model inference. False discarded a planned
call, true executed it and delivered the same mail, and explicit interruption
with true stopped it. This is bounded scheduling evidence, not a universal fix
for cancellation, transport, account or context-limit failures.
The stop check interrupted sampling before command dispatch; cancellation of an
already running tool and human steering were not retested in this experiment.

The [pinned feature registry](https://github.com/openai/codex/blob/4f093f2748667f3b0e6a07e3d4055121cbd3ce64/codex-rs/features/src/lib.rs#L1592-L1597)
and [mailbox scenario tests](https://github.com/openai/codex/blob/4f093f2748667f3b0e6a07e3d4055121cbd3ce64/codex-rs/core/tests/suite/scenarios_mailbox_preemption_tests.rs)
define that boundary. `agents.interrupt_message` controls a history marker and
is retained. Do not disable unrelated interruption or permission controls, change
models, recreate jobs or claim success for a cancelled call. After an update,
regenerate only the selected source's ignored primary settings and verify the
actual new launch. Previously loaded/frozen sessions retain their prior settings.
