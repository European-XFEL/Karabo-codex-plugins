# Branch Material

## Provenance

The original source map summarized locally available Framework branch refs.
A focused source inspection subsequently informed C01–C10, including the newer
AMQP revision below. No C++ builds or runtime tests were run. The hashes pin
the material even if branch names later move.
Paths in the tables are relative to the Framework repository, not this plugin.

| Branch | Base (excluded) | First commit | Tip (included) | Scope |
| --- | --- | --- | --- | --- |
| `cpp20-cobalt-evaluation` | `0f2832f69835a74405ab7b53cc576583453363fd` | `7fac0a3fe` | `51030d421` | 28 commits; 13 files |
| `add-coro-tcp-api` | `4de7c901685c8b4781d14b3244fc3d3b97afb03f` | `a46ccb05c` | `93f126583` | 15 commits; 15 files |

The TCP branch does not include the AMQP branch's commits. Inspect base-to-tip
changes, not a direct diff against today's main, when extracting branch work.
For source inspection, `git diff <base> <tip>` and
`git show <tip>:<path>` reproduce these snapshots without checking out a branch.
If the objects are unavailable, report that limitation rather than silently
substituting another revision. Do not infer MR URLs or approval status from
branch names.

## AMQP and Broker Operations

The AMQP branch adds awaitable operations alongside existing
callback and synchronous entry points. Much of the implementation adapts
callbacks through `boost::cobalt::op` and exposes `cobalt::task` results.
Message reception still uses handlers; this is not a coroutine device API.

| Source path | Material to consult |
| --- | --- |
| `src/karabo/net/AmqpConnection.hh` | `connectCoro`, `ConnectCoro`, channel readiness helper, and `make_copyable_function` for callback adaptation |
| `src/karabo/net/AmqpClient.hh` | `subscribeCoro`, `unsubscribeCoro`, `unsubscribeAllCoro`, `publishCoro`; awaitable `ready` and `initiate` paths |
| `src/karabo/net/AmqpHashClient.hh` and `.cc` | Hash-level coroutine methods forwarding to the raw client; shared serialization for publishing |
| `src/karabo/net/Broker.hh` | New pure virtual coroutine methods on the broker interface |
| `src/karabo/net/AmqpBroker.hh` and `.cc` | Connection, subscriptions, signal/direct/broadcast publishing, reading and heartbeat operations; strand-posted handler state; joined subscriptions |
| `src/brokerMessageLogger/brokerMessageLogger.cc` | Coroutine connection/subscription setup, parallel default subscriptions, and spawning onto the EventLoop |
| `src/karabo/tests/net/testAmqp.cc` | Coroutine connection, raw-client and Hash-client scenarios |
| `src/karabo/tests/net/testBroker.cc` | Connect/disconnect, publish/subscribe, heartbeat and producer/consumer restart scenarios; channel-based coordination |

Lower-level operations commonly return `boost::system::error_code`; broker
operations also translate failures into Karabo exceptions or logging. These
are observed boundaries, not a settled error policy.

`make_copyable_function` bridges move-only completion state to copyable callback
interfaces. Its presence does not establish ownership, cancellation, executor,
or exactly-once completion guarantees for every adapter. See C02–C05 and the
newer adapter implementation below.

The pure virtual additions to `Broker` affect derived implementations. Do not
treat adding such methods as automatically compatible; see C08.

## TCP and WebSocket Transports

This branch adds separate transport implementations selectable
through the existing connection factory, with `cobalt::promise` return types.

| Source path | Material to consult |
| --- | --- |
| `src/karabo/net/Connection.hh` | `startCoro`, `startCoroAsync`, and coroutine connection handler type |
| `src/karabo/net/Channel.hh` | Coroutine read/write overloads and `closeCoro`; default unsupported operations and forwarding helpers |
| `src/karabo/net/TcpConnectionCoro.hh` and `.cc` | Factory ID `TcpCoro`; awaitable client connect; server `startAsync` using a coroutine listener and callback notification |
| `src/karabo/net/TcpChannelCoro.hh` and `.cc` | Raw bytes, vectors, Hash, header/body and BufferSet operations; framing and serialization |
| `src/karabo/net/WebSocketConnectionCoro.hh` and `.cc` | Factory ID `WebSocketCoro`; Beast/Cobalt connection and handshake operations; server coroutine handler |
| `src/karabo/net/WebSocketChannelCoro.hh` and `.cc` | Binary Hash message exchange and coroutine close |
| `src/karabo/tests/net/testTcpCoroNetworking.cc` | Hash round trip, header/body round trip, and BufferSets containing NDArrays |
| `src/karabo/tests/net/testWebSocketCoroNetworking.cc` | Hash echo scenario using five clients |

TCP and WebSocket expose different server startup interfaces. The added classes
are not evidence of a complete replacement for every existing Channel method.
The changed files do not migrate existing devices or pipelines.

Use C06-C09 before selecting shutdown, framing, queue, interoperability, or
device integration conventions. Resolve questions through scoped source
inspection when requested.

## Newer AMQP Revision and Framework Contracts

Additional snapshot: `cpp20-cobalt-evaluation` at
`cf9b965c956bdfc6541d9b9225fcc16ea0f0ae4b` (abbreviated `cf9b965c`). This was
inspected separately; the original snapshot above remains reproducible.
Local uncommitted Framework changes were not used as evidence.

| Source at `cf9b965c` | Change relevant to the skill |
| --- | --- |
| `src/karabo/net/AmqpConnection.hh`, `AmqpClient.hh` | Main callback adapters now retain shared owners, remove direct readiness checks, and use `makeCoroCompletionHandler`. Lazy public methods still borrow arguments. |
| `src/karabo/net/utils.hh` | Completion helper stores the move-only handler and posts invocation to its executor. No cancellation hookup or duplicate-completion guard is supplied. `make_copyable_function` moved here. |
| `src/karabo/net/Strand.hh` | `strand_post_op` moved here and routes completion through the helper. |
| `src/karabo/net/AmqpClient.cc` | Publishing, postponed-message queue, and reconnect behavior support C05/C09. |

Additional Framework sources inspected at `51030d421`:

- `extern/conanfile.txt`, `extern/conanprofile.karabo`, and
  `src/karabo/cmake/karaboPackageDependencies-GNU-Linux-x86.pc.in`: C01.
- `src/karabo/net/EventLoop.cc`: shared event-loop runners (C02).
- `src/karabo/xms/SignalSlotable.hh/.cc`: `AsyncReply`, slot registration,
  and reply dispatch (C04/C07).
- `src/karabo/core/Device.cc`: `slotCallGuard`, `updateState`, and
  `slotKillDevice`/`preDestruction` (C06/C07).

Use `git show <revision>:<path>` to reproduce a source observation. The detailed
answers and remaining questions live in [C01–C10](open-decisions.md).

## Build Material

Both branches update `src/karabo/CMakeLists.txt` and
`src/karabo/cmake/karaboPackageDependencies-GNU-Linux-x86.pc.in` for Cobalt.
The TCP branch also links `Boost::cobalt_io`. The AMQP branch conditions its
`-Wno-mismatched-new-delete` suppression on GNU compiler versions below 15;
the TCP branch adds that suppression without the same condition.

[C01](open-decisions.md#c01--supported-toolchain-and-dependencies) records the
project-selected toolchain matrix and GNU-only warning suppression below
version 15. Build/export validation remains open; the branch configurations
are historical examples.

## Library References

Consult documentation matching the selected Boost version when implementing:

- [Boost Cobalt documentation](https://www.boost.org/doc/libs/latest/libs/cobalt/doc/html/index.html)
- [Boost Cobalt source](https://github.com/boostorg/cobalt)

These links are discovery entry points, not a pinned compatibility promise.
C01 and C02 record the chosen baseline and execution preferences, with
versioned references and remaining validation work.
