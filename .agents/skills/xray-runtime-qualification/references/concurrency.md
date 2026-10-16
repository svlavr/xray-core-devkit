# Concurrency and lifecycle mode

Read only for an implicated owner/transition. Pin the actual source, selected
build and caller contract; map state and shared/borrowed resources before
proposing a safeguard. Trace creation, admission, transfer, blocked I/O,
cancellation, publication, Close, drain and join. Name the actor at each step,
lock/publication order, wait edges, allowed late results and promised completion.
Distinguish data races, logical races, deadlocks and valid retained native work.

`mu_concurrency_reviewer` supplies that trace plus a concrete interleaving and
deciding observation where a risk exists. Use deterministic barriers or a
bounded watchdog rather than timing sleeps as proof. Include cancellation while
blocked, a surviving shared sibling, reentry and publication/retirement races
only where the path reaches them. Preserve rejected-buffer custody and existing
packet/batching semantics. Do not close shared transports to make one caller
finish, or invent universal joins, late-result suppression or immutable returns.

The test architect checks assertion sensitivity against a broken control.
An assigned worker runs focused source tests/race jobs through the managed runner
and reports exact commands, selected source/build, failed access pairs and
progress/cleanup observations. Race-clean does not establish logical progress;
a watchdog firing needs its retained failure evidence. Keep fixture cleanup
distinct from a guarantee that all native asynchronous work joined.

Disposition fixture races only under this project's explicit owner policy and
actual conflicting access pair/source/build configuration. Preserve every failed
attempt; historical filename-level exceptions do not qualify changed code.
Return scoped CLEAN or grounded findings, unresolved interleavings and gates.
Security inspects trust reachability and performance measures cost separately;
critical review reconciles their real interactions on stable integrated bytes.
