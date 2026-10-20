# Coroutine Guidance and Remaining Questions

- **PD — Project Decision:** choices supplied for Karabo, including provisional
  preferences.
- **UG — Upstream Guidance:** contracts or recommendations from official library
  documentation, source, or the C++ Core Guidelines.

Code observations include a Framework revision and symbol; they describe the
implementation at that revision, not a project-wide recommendation. The
[source map](branch-material.md) identifies the snapshots. Source inspection
supports the answers below; no C++ builds or runtime tests were run for this
update. Remaining questions are collected at the end of each section.

## C01 — Supported Toolchain and Dependencies

**PD:** use C++20 (`-std=c++20`), g++ 10 or newer, and Boost 1.89.0 or newer.
Current project configurations use Boost 1.91.0:

| Platform | Compiler |
| --- | --- |
| Red Hat 9 | g++ 11 |
| Ubuntu 22 | g++ 11 |
| Ubuntu 24 | g++ 13 |
| Ubuntu 26 | g++ 15 |

**PD:** obtain dependencies from Conan Center. For GNU compiler versions below
15, apply `-Wno-mismatched-new-delete` to suppress false positives.

Code (`51030d421`): `extern/conanfile.txt` requires `boost/1.91.0`, enables
`boost/*:without_cobalt=False` and shared libraries, and uses `CMakeDeps`,
`CMakeToolchain`, and `PkgConfigDeps`. `extern/conanprofile.karabo` includes the
local default profile and sets `compiler.cppstd=gnu20`,
`compiler.libcxx=libstdc++11`, and Release builds. Thus the profile enables GNU
C++20 extensions; it does not pin a compiler version by itself.
`src/karabo/CMakeLists.txt` links `Boost::cobalt` and conditions the warning
suppression on GNU < 15. The pkg-config dependency template exports
`boost-cobalt`. At `93f126583`, the transport build also links
`Boost::cobalt_io` but applies the warning suppression unconditionally; use
the PD condition when adapting that configuration.

**UG:** Cobalt I/O is present in the
[Boost 1.89 documentation](https://www.boost.org/doc/libs/1_89_0/libs/cobalt/doc/html/index.html).

**Open:** Which complete Conan profiles and export/link checks validate the
minimum versions and each supported platform? The available recipe and profile
answer configuration questions, but do not prove those builds succeed or that
all required package binaries are available from Conan Center.

## C02 — Coroutine Types and Execution Context

**PD:** prefer `cobalt::promise<T>` wherever practical. I/O out → `promise`,
I/O in → `task` is a preference; choose lazy execution when needed, including
entry tasks passed to `spawn`.

**UG:** `promise` is eager and `task` lazy. `generator` retains state across
yields and can defer work with `cobalt::this_coro::initial`. Awaiting observes
completion; an eager coroutine can finish before being awaited.
[Type guidance](https://www.boost.org/doc/libs/1_89_0/libs/cobalt/doc/html/index.html#promises).

**PD:** enter coroutine execution from synchronous Karabo applications and
unit tests with `cobalt::spawn(executor, task, completion_token)`. Use the
appropriate EventLoop executor and keep its loop running. Handle results and
exceptions through the completion token when they matter; `asio::detached`
discards completion notification. Other entry mechanisms are `co_main`,
blocking `cobalt::run(task)`, and a coroutine returning `cobalt::thread` that
can be joined.

**UG:** `spawn` dispatches initiation and posts completion. For strands,
explicitly supply the executor to nested promises/generators using
`asio::executor_arg_t`, and to channels through their constructor. Thread-local
lookup does not preserve strand association. Cobalt restricts cross-thread
resumption, with an exception for tasks; this is not general permission to
move coroutine state between threads.
[Spawn](https://www.boost.org/doc/libs/1_89_0/libs/cobalt/doc/html/index.html#spawn),
[strands](https://www.boost.org/doc/libs/1_89_0/libs/cobalt/doc/html/index.html#using_strands),
[threading](https://www.boost.org/doc/libs/1_89_0/libs/cobalt/doc/html/index.html#threading).

Code (`51030d421`): `EventLoop::addThread` can add runners to the shared I/O
context, while `AmqpConnection` owns a separate single-threaded I/O context for
AMQP. `AmqpBroker` posts handler/subscription bookkeeping to its Karabo
`m_handlerStrand`. These are distinct execution contexts. At `cf9b965c`,
`makeCoroCompletionHandler` posts AMQP completion to the coroutine handler's
executor; see C03. A strand serializes handlers, not an entire workflow across
suspension. Slot/state implications are in C07.

**PD:** use Asio's `experimental::concurrent_channel` for cross-thread channel
communication. The supplied Cobalt `example/thread.cpp` exchanges requests,
results, and exceptions, closes its request channel, and joins workers.
`example/thread_pool.cpp` demonstrates spawn completion handling. Consult the
selected release's [examples](https://www.boost.org/doc/libs/1_89_0/libs/cobalt/doc/html/index.html#advanced_examples).
The response-channel pointer in the worker example still needs to outlive its
pending request; it does not establish cancellation-safe device ownership.

**Open:** Validate the supplied Cobalt adaptation of the
[executor-switching example](https://stackoverflow.com/questions/79905678/how-to-correctly-migrate-awaitables-between-different-execution-contexts)
(dispatch to a pool strand with `bind_executor(strand, deferred)`, then dispatch
with `deferred` to return), including allocator lifetime and continuation
threads. Original attribution: Max and community, CC BY-SA 4.0; supplied
retrieval date 2026-09-24. Which executor/strand should own each new device's
operations and state? Existing AMQP routing does not settle that device policy.

## C03 — Callback Adapters and Completion

**PD:** provisionally use `cobalt::op` for adapting Karabo callbacks at the
`AmqpClient` level. The preference is based on interface simplicity and PMR
support; revisit it as implementation experience accumulates. A future
coroutine-native AMQP implementation, possibly including AMQP-CPP's I/O layer,
is a direction, not work required by this skill.

**UG:** implement `initiate`; override `ready` only for a safe immediate path.
The base `ready` is a no-op. Completion handlers expose executor, allocator,
and cancellation-slot associations.
[Operation source](https://github.com/boostorg/cobalt/blob/boost-1.89.0/include/boost/cobalt/op.hpp),
[handler source](https://github.com/boostorg/cobalt/blob/boost-1.89.0/include/boost/cobalt/detail/handler.hpp).

Code (`cf9b965c`): `ConnectCoro`, `SubscribeCoro`, `UnsubscribeCoro`,
`UnsubscribeAllCoro`, and `PublishCoro` hold shared pointers to their owners.
Their earlier direct `ready` state checks have been removed. They delegate to
the existing asynchronous APIs through `makeCoroCompletionHandler` in
`src/karabo/net/utils.hh`. That helper stores the move-only completion handler
in a shared pointer, copies/moves callback arguments into a tuple, and always
posts invocation to `complete.get_executor()`. This handles callbacks arriving
on the AMQP thread or during initiation without directly resuming there.

The helper does not forward an associated allocator to its `make_shared` or
posted lambda, connect cancellation to the underlying AMQP operation, or guard
against repeated callback invocation. `make_copyable_function` alone supplies
none of these guarantees. `strand_post_op` also uses the completion helper,
but does not catch exceptions from its posted function. Do not treat either
adapter as a complete error/cancellation template.

**Open:** How should callback cancellation and late completion work, and who
owns exactly-once arbitration when success, failure, and cancellation compete?
Which allocator propagation is required? How should `strand_post_op` deliver
a thrown exception to its awaiting coroutine? Validate these cases before
promoting the adapter into a general template.

## C04 — Ownership Across Suspension

**UG:** pass owned arguments by value when they must survive suspension;
references require a lifetime guarantee covering the whole operation. Avoid
capturing coroutine lambdas whose closure can die while suspended. Never hold
a blocking lock across an await. See C++ Core Guidelines
[CP.51–CP.53](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#SScp-coroutines).
A by-value `shared_ptr` retains its pointee; a `this` pointer or a reference to
a `shared_ptr` does not provide the same ownership.

Code (`cf9b965c`): AMQP adapter objects now retain their owners, but lazy member
entrypoints such as `subscribeCoro(const std::string&, const std::string&)`
still borrow arguments and only call `shared_from_this()` after starting.
Callers must keep the object and borrowed arguments alive until that work runs;
calling the member and storing its task does not itself retain the owner.

Code (`93f126583`): Hash write overloads serialize into local archives that
remain in the coroutine frame across the write. Raw-buffer and BufferSet
paths build buffer views over caller data. Retain that storage and avoid
mutation until the write completes; retaining a view is insufficient.
This also applies to shared NDArray backing storage.
[Beast's buffer lifetime contract](https://www.boost.org/doc/libs/1_89_0/libs/beast/doc/html/beast/ref/boost__beast__websocket__stream/async_write.html).

**Open:** Should a device operation retain the device until completion, or use
weak ownership and stop on removal? Define both memory retention and pending
reply behavior (C06–C07). The branches do not provide that device-level policy.

## C05 — Errors, Timeouts and Cancellation

Code (`51030d421`): AMQP adapters expose `error_code`; `AmqpBroker::connectCoro`
translates failure into a Karabo network exception. `publishCoro` logs voluntary
message drops and throws for other failures. Preserve these operation-specific
boundaries when converting callers.

Code (`93f126583`): transport reads/writes return `(error_code, size_t)` tuples,
but serialization and setup may still throw. `TcpConnectionCoro::startClient`
throws Karabo network exceptions on resolve/connect failure. A tuple return
therefore does not make the entire API non-throwing.

**UG:** Cobalt cancellation uses Asio cancellation signals; custom awaitables
must participate. A timer winning a race is not evidence that a callback-based
operation has stopped.
[Cancellation](https://www.boost.org/doc/libs/1_89_0/libs/cobalt/doc/html/index.html#cancellation).

Code (`cf9b965c`): AMQP's completion bridge has no cancellation hookup.
`AmqpClient::reviveIfReconnected` restores channel/subscriptions and postponed
publishing; it does not establish an exactly-once delivery guarantee.
`doPublish` signals success when AMQP-CPP's `publish` accepts the message;
its comments explicitly note that later network errors may follow. Do not
interpret successful completion as consumer receipt or processing.

**Open:** Choose operation-specific deadlines, cancellation/late-completion
handling, and retry/idempotency policy. A universal error translation policy
for new device APIs cannot be inferred from the different branch boundaries.

## C06 — Background Work and Shutdown

Code observations:

| Operation | Behavior at the inspected revision |
| --- | --- |
| `AmqpBroker::disconnectCoro` (`51030d421`) | Resets its client; leaves the shared connection alive. |
| `AmqpBroker::stopReadingCoro` (`51030d421`) | Awaits unsubscribe-all and clears handlers through the handler strand. |
| `TcpChannelCoro::close` (`93f126583`) | Cancels and closes the socket synchronously; does not join suspended callers. |
| `TcpConnectionCoro::stop` (`93f126583`) | Resets the acceptor member; the listener can retain a local shared pointer while awaiting accept. This is not proof that stop cancels the pending accept. |
| `WebSocketChannelCoro::closeCoro` (`93f126583`) | Awaits the WebSocket close handshake, logs its error, then closes the underlying stream. |
| `Channel::closeCoro` (`93f126583`) | Default throws unsupported; TCP does not override it in this snapshot. |

**UG:** stopping an Asio I/O context stops event processing; it is not a join of
pending operations. Keep required executors running while awaiting cleanup.
[Asio stop](https://www.boost.org/doc/libs/1_89_0/doc/html/boost_asio/reference/io_context/stop.html).

Code (`51030d421`): `Device::slotKillDevice` invokes synchronous
`preDestruction()`. Neither inspected branch supplies a device task owner or an
asynchronous destruction protocol. C02's completion token can observe a spawned
task's outcome, but does not by itself track all device background work.

**Open:** Define task ownership, listener/timer cancellation, draining, reconnect
coordination, and removal with pending I/O. When is detached work acceptable?
Add a lifecycle example before choosing a general device shutdown convention.

## C07 — Device Slots, Replies and State

Code (`51030d421`, `SignalSlotable.hh/.cc`): registered slots use `void`
callbacks. Existing APIs permit a synchronous slot wrapper to create
`AsyncReply`, start separate coroutine work, and return. Returning a Cobalt
type directly from a registered callable does not make slot dispatch await it.
The wrapper must preserve these existing `AsyncReply` requirements:

- Construct it inside the original slot call, before returning.
- Complete a copy once through success or `error`, after leaving the original
  slot execution context; do not assume an eager coroutine necessarily suspends.
- Keep its `SignalSlotable` alive. `AsyncReply` contains a raw pointer and must
  not be used during or after destruction.

`registerAsyncReply` suppresses the automatic reply; `operator()` and `error`
do not contain a shared completed flag. Exactly-once completion is a caller
obligation, not protection supplied by copying `AsyncReply`.

Code (`51030d421`, `Device.cc`): `slotCallGuard` checks lock/state at slot entry.
It does not run again when a coroutine resumes. Recheck operation-specific
state and shutdown conditions before applying results after suspension.
`updateState` uses `set` and can place a synchronous reply; an asynchronous
reply still needs explicit completion. Internal property locking does not
serialize a whole suspended operation against reconfiguration or another slot.

**Open:** Define the device executor and permitted overlap with reconfiguration,
plus success/error/cancellation reply ownership during shutdown. A complete
reference device and lifecycle tests are still needed. A wrapper is feasible
with existing APIs; its full lifecycle contract has not been demonstrated.

## C08 — Existing API and Transport Compatibility

Code (`51030d421`): callback and synchronous AMQP APIs coexist with coroutine
entrypoints. Added pure virtual `Broker` methods require derived classes to
implement them. Code (`93f126583`): `TcpCoro` and `WebSocketCoro` are separate
factory implementations; default `Channel` coroutine methods throw or forward
to other overloads. Check the actual overload rather than assuming parity.

Framing observations (`93f126583`): TCP uses configured length prefixes and
serialization, with distinct raw, Hash, header/body and BufferSet paths.
BufferSet writes require length framing and reject text serialization.
WebSocket writes a binary Hash archive prefixed by an `unsigned int` size;
reads skip that prefix. This describes the implementation, not validation of
malformed input or interoperability across versions and platforms.

Existing synchronous AMQP methods wait for callbacks. Never block the AMQP
I/O thread or another executor needed to deliver the awaited completion.
`AmqpBroker`'s callback routing comments explicitly identify this deadlock risk.

**Open:** Which source/ABI guarantees are required for external C++ plugins?
Which Python bindings should expose coroutine functionality? Which old/new
endpoint combinations must interoperate? Existing code and round-trip tests
do not establish those project compatibility requirements.

## C09 — Ordering, Queues and Streaming

**UG:** Beast disallows overlapping writes on one WebSocket stream and requires
buffer storage to survive completion. Serialize whole writes, not just their
initiation; a strand alone does not prevent overlap after suspension.
[Write contract](https://www.boost.org/doc/libs/1_89_0/libs/beast/doc/html/beast/ref/boost__beast__websocket__stream/async_write.html).

Code (`93f126583`): TCP coroutine writes directly await `cobalt::io::write`;
WebSocket writes directly await Beast. The coroutine write paths do not enqueue
through the stored legacy priority queues. `queueInfo` and
`setAsyncChannelPolicy` existing on these classes are therefore not evidence
that those policies govern coroutine writes. Shared receive buffers and
multi-step framing also require serialized reads unless a specific overload
proves otherwise. Buffer ownership is covered in C04.

Code (`cf9b965c`, `AmqpClient::postponeMessage`): disconnected publishing queues
up to 1,000 messages and drops the oldest with `eMessageDrop` when full.
Preserve that behavior when adapting this path; it is not a universal transport
queue policy. Completion meaning is covered in C05.

**Open:** Define coroutine queue limits and drop/wait policies, including how
pipeline backpressure, EOS, and disconnect behavior map to these transports.
Neither branch migrates the pipeline layer or validates that mapping. Add
concurrent-operation and slow-consumer scenarios once the contract is chosen.

## C10 — Tests and Validation

Code (`51030d421`): coroutine broker tests include channel coordination,
producer/consumer restarts, and spawn completion handlers. Some handlers print
exceptions rather than fail the test; some restart tests use unbounded
`future.get()`. Code (`93f126583`): TCP tests check Hash, header/body and
BufferSet/NDArray round trips, while WebSocket exercises five clients. Top-level
transport tasks use detached spawn and `EventLoop::run()`. These are useful
scenario sources, not complete failure-reporting or bounded-cleanup templates.

For new tests, carry spawn failure into an assertion, bound the wait, and
retain execution/operation ownership through cleanup. This follows from the
specific gaps above. A timeout must fail the test and initiate cleanup, not
permit teardown while handlers still reference destroyed state. Coordinate
observable milestones with channels or completion signals rather than assuming
an arbitrary delay proves progress.

**UG:** Cobalt's versioned
[`test/op.cpp`](https://github.com/boostorg/cobalt/blob/boost-1.89.0/test/op.cpp)
provides ready/deferred and error/exception examples. Its coverage does not
establish cancellation or lifetime correctness of Karabo's adapters.

**Open:** Run the selected build/test matrix, add adapter cancellation and
late-completion cases, and demonstrate device removal and mixed-endpoint
behavior. Select sanitizer/load checks based on the lifetime and concurrency
contracts being exercised. Record commands, environment, results, and untested
cases before claiming runtime validation; performance claims need measurements.
