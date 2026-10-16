# Controlled performance, profiling and load mode

Assign `mu_performance_reviewer` either measurement design or independent review
of stable candidate/results. Use a different instance where independence from
its own design matters. Pin baseline/candidate, workload and achieved work,
payload, route/connection reuse, concurrency, warmup, toolchain/platform,
resource limits and cancellation semantics. Include meaningful correctness and
ownership controls before interpreting a faster candidate.

Main assigns actual benchmarks/profiles/load to a worker through the managed
runner, with exact scratch/output and bounded duration. Separate uninstrumented
latency/allocation runs from CPU, allocation, retained-heap, mutex/block and race
instrumentation. Use native Go benchmarks/profiles and appropriate comparison
tools when available; dependency installation needs its normal explicit scope.
Record interference and variability; repeat only when it can change selection.
Do not convert a sequential fixture into a concurrency-bottleneck claim.

Attribute measured work to reachable owners and distinguish fixed layout, stack
growth, allocation churn, retained memory and unbounded growth. Removing a heap
allocation may shift cost to stacks or alter borrowed-buffer custody. A failed
semantic/native countercontrol disqualifies a speed claim. Profile samples and
microbenchmarks explain their workload, not an unmeasured product/device path.

For controlled overload and backpressure, distinguish offered/admitted work,
completed delivery, queued work, drops/loss and recovery. Observe cancellation,
surviving siblings and cleanup at the selected queue/owner where relevant.
An underdriven fixture is not capacity evidence; bytes offered or copied do not
prove remote delivery, and an unattributed deficit is not a diagnosed cause.
Do not introduce production quotas, batching changes or retry layers merely to
make the measurement convenient.

Return causal measurements, validity controls, limitations and next deciding
observation. Concurrency owns progress/custody, security owns reachable trust
effects, and performance owns attributable cost/saturation. Main combines their
evidence with real-consumer regression and stable review before accepting an
optimization. No universal latency win, device result or release gate follows.
