# Threat model output contract

Use these sections in order:

1. `Executive summary`
2. `Scope and assumptions`
3. `System model` with primary components, trust-boundary bullets, and one
   conservative Mermaid `flowchart` using quoted labels
4. `Assets and security objectives`
5. `Attacker model`
6. `Entry points and attack surfaces`
7. `Top abuse paths`
8. `Threat model table`
9. `Criticality calibration`
10. `Focus paths for security review`
11. `Open questions and residual risk`

Threat IDs must be stable (`TM-001`, `TM-002`, ...). Each major claim needs one
or two repository path/symbol anchors. Table fields must include prerequisites,
action, impact, assets, controls, gaps, mitigation, detection, likelihood,
impact severity, and priority (`critical`, `high`, `medium`, or `low`).
