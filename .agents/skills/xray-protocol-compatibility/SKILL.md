---
name: xray-protocol-compatibility
description: Review and qualify a changed configuration, protocol, transport or peer interoperability seam through the actual consumer. Use for wire/framing, handshake, DNS/routing or named-peer compatibility claims, not an automatic full protocol matrix.
---

# Qualify the selected protocol seam

Read `docs/PROJECT_SCOPE.md` and the exact owner-supplied behavior contract.
Select the changed seam and real caller, not every protocol in the checkout.
Examples of relevant Xray families are VLESS/VMess, Hysteria, WireGuard, TLS,
REALITY and XHTTP; their names alone do not establish current support or wiring.
Use `xray-code-analysis` for reachable Go ownership and exact build selections.

Main assigns `mu_protocol_reviewer` the configuration-to-consumer question.
Map supported input format -> decode/Build/Start -> DNS result and selected
route/handler -> protocol frame/handshake -> transport -> actual consumer/peer.
Record exact source, peer implementation/version, options and relevant defaults.
Configuration acceptance, local startup, successful wire exchange and peer
interoperability are separate observations. Keep native behavior and explicitly
selected extensions distinguishable without importing another project's policy.

Define only the combinations implicated by the change, including successful and
rejecting handshakes, authentication/trust controls and relevant packet/frame or
decoded-byte vectors. For framing/buffer changes include boundaries, truncation,
partial read/write and packet destinations/custody where meaningful. Do not
infer full-body delivery or remote receipt from a connection, header or byte
counter. Name an unsupported or unknown combination explicitly.

Factual upstream researchers establish changed APIs, defaults, errors, versions
and dependency consumers. The test architect designs assertions that distinguish
native/extension and working/broken cases. An assigned worker actually executes
them through `xray-decision-experiment`; main returns evidence to design and
implementation owners and the behavior reviewer checks the real caller. This
source-to-consumer comparison is required before an upstream update is called
compatible; a compile-green refresh alone cannot establish it.

Use **network-failure mode** when the changed seam needs it: identify concrete
ingress/outbound, injected fault point (resolver failure, peer reset, stalled
carrier), expected consumer-visible error/cancellation/cleanup and a live sibling
or other countercontrol when relevant. Run only authorized scoped experiments;
host injection does not prove live-network or device behavior. No extra failure
experimenter profile or production retry/quota layer is introduced.

Use `xray-runtime-qualification` and only its implicated mode for lifecycle,
trust, performance or target/ABI questions. Keep source/host, wire peer, live
network, artifact/device and release gates separate. Main owns selection,
integration and explicitly authorized publication. No fixed roster, mandatory
matrix, new runtime or automatic device acceptance follows from this skill.
