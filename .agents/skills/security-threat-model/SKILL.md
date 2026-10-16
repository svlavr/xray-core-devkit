---
name: security-threat-model
description: Build a repository-grounded threat model for Xray Core. Use only when the user explicitly asks to threat model the repository or a path, enumerate threats or abuse paths, or perform AppSec modeling. Do not use for general architecture summaries, ordinary code review, or non-security design work.
---

# Xray fork threat model

Create a concise AppSec threat model grounded in exact repository paths. Do not
trigger for ordinary architecture explanation or code review.

1. Define in-scope paths, deployment assumptions, entrypoints, and exclusions.
   Separate upstream code, fork changes, build/CI, tests, core bindings, core
   artifacts, and downstream consumers.
2. Map trust boundaries for network inputs, configurations, control/API clients,
   DNS/routing, outbound transports, local files, secrets, native/platform
   integration, build provenance, and update/publication channels when present.
3. List assets and realistic attacker capabilities/non-capabilities. Never expose
   discovered secrets; only describe and redact their location.
4. Write a small set of concrete multi-step abuse paths tied to evidence. Rate
   likelihood and impact with explicit assumptions and existing controls.
5. Before finalizing, ask the user 1вЂ“3 questions only when deployment, exposure,
   privilege, multi-user use, or sensitive data would materially change rank.
6. Tie mitigations to exact components and distinguish existing controls from
   recommendations. Include detection and residual risk for high items.
7. Produce one compact Mermaid data-flow diagram. A write-authorized main task
   saves the report only at an explicitly scoped work-document path. A read-only
   child returns the report to main and creates or edits no file; a child may
   write a report only when its dispatch names that exact path in its write set.

Use `references/output-contract.md` for the final structure. Prioritize remote
code execution, config/parser abuse, routing or DNS integrity compromise, secret
exposure, control-API authorization, resource exhaustion, unsafe native/binding
boundaries, and supply-chain/release compromise only where evidence supports it.
