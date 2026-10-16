# Routine security review mode

Use for an actual changed attack surface or trust decision. Trace an
attacker-controlled input/capability through parsing and normalization,
route/session/identity/trust state, and a sensitive sink. State exposure,
prerequisites, existing controls, abuse/exploit sequence, impact and a decisive
negative control. A candidate weakness without reachable exposure is not the
same finding as an exploitable path.

`mu_security_reviewer` assesses implicated wire/configuration parsing, native
control APIs, callbacks/files, authentication/TLS trust, pooled trust or route
reuse, logging, socket/DNS/platform privilege and admission/resource exhaustion.
Use only reachable owners in the accepted scope; do not inherit a consuming
application's policy or add arbitrary hardening limits. Dependency/advisory
research supplies exact affected versions and facts, while local source and
consumer controls establish applicability.

Test architect designs meaningful rejecting controls and retained valid native
cases. Main assigns authorized reproduction/repair to a worker; no unapproved
live exploitation, network access, account operation or secret disclosure.
Redact raw sensitive inputs from review artifacts. Keep observed, inferred and
unavailable evidence separate. Return a scoped CLEAN when supported, or a
grounded trigger, trust-to-sink path, consequence and smallest necessary repair;
no minimum issue count or blanket policy rewrite.

Routine review does not invoke `security-threat-model` automatically. That
existing skill remains for an explicit broader threat-model/AppSec-modeling
request. Concurrency, artifact and cross-boundary critical reviews retain their
separate evidence duties. A security verdict does not grant release authority.
