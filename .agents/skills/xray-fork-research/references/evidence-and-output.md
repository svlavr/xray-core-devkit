# Evidence and output

## Evidence order

1. exact official upstream source, specification, or security policy;
2. current fork baseline, code, tests, and accepted fork documents;
3. a bounded experiment matching the real call path;
4. exact source behavior in an independently licensed implementation;
5. issue, PR, release note, or dated project statement;
6. historical/local behavior or community reports.

Lower evidence may expose a gap but cannot silently override higher evidence.

## Verdicts

- `UPSTREAM_HAS_IT`: official upstream already solves the requirement.
- `FORK_GAP`: the required behavior is absent at the relevant boundary.
- `PARTIAL`: useful support exists but an exact gap remains.
- `NOT_NEEDED`: the proposed mechanism does not serve the stated requirement.
- `DEFER`: the decision belongs to a later core-artifact or release gate.
- `EXPERIMENT_REQUIRED`: current evidence cannot choose safely.

Lead with the verdict, decisive evidence, fork applicability, risks and license
limits, what remains unproven, and the smallest next action.
