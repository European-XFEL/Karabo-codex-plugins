# Open Decisions and Missing Examples

All items below are **TODO**. They are intentional work items, not executable
instructions or established conventions. Record questions here while developing
the skill; resolving them does not belong to an implicit Framework code review.
The separate migration project owns rollout ordering and component inventories.

## C01 — Supported Toolchain and Dependencies

- [ ] TODO: Which C++ standard, compiler versions, Boost release and Cobalt I/O
  version are supported? Is Cobalt I/O available in the selected release?
- [ ] TODO: Which build/export dependencies and warning workarounds are needed?

Completion evidence: an agreed version matrix, versioned upstream references,
and validated build/export examples for the supported configurations.

## C02 — Coroutine Types and Execution Context

- [ ] TODO: When should public/internal APIs return lazy `task`, eager `promise`,
  or an operation adapter? Reconcile the two branches' choices.
- [ ] TODO: How are coroutines started on Karabo's EventLoop, and which executor
  or strand owns each operation and its continuation?
- [ ] TODO: Which Cobalt objects can be used across execution contexts? How are
  cross-thread messages delivered, and when is `concurrent_channel` required?
- [ ] TODO: What reentrancy is permitted when device work suspends and another
  slot or reconfiguration runs?

Completion evidence: an execution contract and reviewed examples for one
operation, composed operations and communication across execution contexts.
Use version-specific Cobalt rules; coroutine syntax alone does not serialize
shared device state.

## C03 — Callback Adapters and Completion

- [ ] TODO: Should new adapters use the branch's custom `cobalt::op` pattern or
  an existing completion-token mechanism? Which cases justify each approach?
- [ ] TODO: What are the contracts for immediate readiness, callback completion,
  exceptions, cancellation and callbacks arriving after cancellation?
- [ ] TODO: How are move-only handlers, associated executors and allocators
  preserved when bridging copyable callback APIs?

Completion evidence: reviewed adapter examples with immediate and deferred
completion, failure and cancellation tests demonstrating one completion and
valid state lifetimes.

## C04 — Ownership Across Suspension

- [ ] TODO: Who owns a device operation, and what happens to it when the device
  is removed? When should code retain shared ownership or acquire a weak owner?
- [ ] TODO: Which arguments must be owned by value? Define rules for references,
  coroutine lambda captures, `this`, and data passed into lazy tasks.
- [ ] TODO: How long must serialized buffers, BufferSets and NDArrays remain
  alive and unchanged during an outstanding write?

Completion evidence: reviewed ownership examples and tests where callers,
connections or devices disappear while work is pending. Address memory
retention as well as premature destruction.

## C05 — Errors, Timeouts and Cancellation

- [ ] TODO: Where should failures use exceptions, error codes, result values or
  null returns? Define translation at transport, framework and device boundaries.
- [ ] TODO: How are deadlines applied, and does timeout cancel and complete the
  underlying work? What happens if completion races with cancellation?
- [ ] TODO: How do wrappers over existing callbacks propagate cancellation?
- [ ] TODO: Which failures are retried, and how is duplicate completion or
  duplicate message delivery handled?

Completion evidence: an error/cancellation contract plus failure, timeout,
cancellation and late-completion examples with observable assertions.

## C06 — Background Work and Shutdown

- [ ] TODO: Who tracks spawned operations and observes their exceptions?
  Under what conditions, if any, is detached work appropriate?
- [ ] TODO: How do shutdown, reconnect and device destruction cancel reads,
  listeners and timers, then wait for their completion?
- [ ] TODO: What do `stop`, `close` and `closeCoro` guarantee? How is teardown
  coordinated without blocking the executor needed to finish it?

Completion evidence: a lifecycle example covering startup, background work,
normal close, connection loss and removal with pending I/O. Include explicit
expectations for remaining tasks, handlers and resources after shutdown.

## C07 — Device Slots, Replies and State

- [ ] TODO: How does a synchronous registered slot enter a coroutine workflow?
  Is new framework support needed, or can a defined adapter use existing APIs?
- [ ] TODO: How is `AsyncReply` completed exactly once on success, failure and
  cancellation, including device shutdown?
- [ ] TODO: Where may coroutine continuations update properties and state?
  Which existing state/lifecycle checks still apply after an await?
- [ ] TODO: Add a complete example device with initialization, an awaited slot
  operation, a periodic or subscription task, and teardown.

Completion evidence: reviewed device-level conventions and tests for the
observable slot/state/reply lifecycle. Neither source branch currently serves
as this complete reference example.

## C08 — Existing API and Transport Compatibility

- [ ] TODO: How are callback and synchronous entry points retained? What source
  and binary compatibility requirements apply to virtual interface changes?
- [ ] TODO: How do existing C++ plugins and Python bindings interact with the
  new APIs? Where are synchronous waits allowed without deadlocking an executor?
- [ ] TODO: Which new/old TCP and WebSocket endpoints must interoperate? Define
  framing, serialization and unsupported-operation expectations.

Completion evidence: an agreed compatibility boundary and mixed old/new caller
and endpoint tests. This defines API behavior, not a rollout schedule.

## C09 — Ordering, Queues and Streaming

- [ ] TODO: Are overlapping reads or writes allowed on a channel? How are
  message order, write serialization and queue limits maintained?
- [ ] TODO: How do existing drop/wait policies and backpressure map to awaited
  writes? What does write completion guarantee to the caller?
- [ ] TODO: Document BufferSet/NDArray ownership together with C04, and identify
  any extra pipeline requirements such as EOS and disconnect behavior.

Completion evidence: defined channel contracts plus concurrent-operation,
slow-consumer, disconnect and large-buffer examples with relevant assertions.

## C10 — Test Patterns and Evidence Promotion

- [ ] TODO: Establish how tests own coroutine execution, surface exceptions,
  impose bounded completion and clean up EventLoop state.
- [ ] TODO: Document deterministic synchronization patterns; assess branch tests
  before promoting them as templates. Test names alone do not prove coverage.
- [ ] TODO: Add scenarios for immediate/deferred completion, errors, timeout,
  cancellation, shutdown, reconnect and compatibility as applicable to each API.
- [ ] TODO: Decide which focused sanitizer or load checks are needed for lifetime
  and concurrency contracts; make performance claims only with measurements.
- [ ] TODO: Once examples are reviewed, exercise the skill on a different
  authorized C++ task and record which guidance was missing or misleading.

Completion evidence: runnable, reviewed examples with recorded environments and
results, plus explicit agreement before a pattern is labelled Established.
