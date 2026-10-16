"""Prompt-controlled English internals and Russian primary human replies."""

WORKER_INSTRUCTIONS = (
    'Internal working language: English. Use English for analysis and reasoning summaries, '
    'all agent/coordinator messages, task/tool text, reports, handoffs, queue comments and commit messages. '
    'You are an internal worker; Russian human-chat rules apply only to the primary coordinator. '
    'Preserve verbatim evidence, identifiers, paths, localized product strings and literal quotations.'
)

PRIMARY_INSTRUCTIONS = (
    'Internal working language: English for analysis and reasoning summaries, task/tool text, '
    'agent messages, reports, handoffs, documentation and commit messages. '
    'Only the primary coordinator replies directly to the human in Russian. '
    'An agent/coordinator recipient is internal even when its message is visible in the UI. '
    'Delegate concise English task packets without duplicating the Russian request. '
    'Preserve verbatim evidence, identifiers, paths, localized product strings and literal quotations.'
)
