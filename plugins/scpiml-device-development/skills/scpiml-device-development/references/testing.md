# Testing And Validation

Read the companion `karabo-device-development` pytest reference for fixture,
proxy, synchronization, and cleanup rules. This reference adds scpiml-specific
protocol contracts.

## Environment And Scope

Use the existing environment referenced by `$KARABO`. Check that it imports
the intended `scpiml` implementation and satisfies the device's declared
dependency. Use an editable install when developing that package. If an
expected dependency is missing, ask for it to be installed in that environment;
do not emulate Karabo imports or change dependency pins just to run tests.

Follow the target repository's pytest-asyncio configuration and
`KaraboTestLoopPolicy` fixture. The inspected framework uses asyncio auto mode
with module loop scopes. Some downstream tests explicitly use function loops;
do not copy those markers into a module-scoped fixture without checking scope
compatibility.

Use a real local TCP boundary for command bytes, framing, reply consumption,
startup, and polling. Pure parsers can be tested without device startup.
Do not mock `sendCommand`, `sendQuery`, or `writeread` when their protocol
behavior is what the test must prove.

## Reusable Simulated Hardware

`from scpiml.tests.mock_hardware import mock_server` provides the async context
manager `mock_server(cls, responses, separator, config=None)`, yielding
`(server, ctx)` with the device at `ctx["device"]`.
The helper creates an ephemeral TCP port, sets a
`socket://127.0.0.1:...` device URL, and starts an `AsyncDeviceContext`.
`ScpiDevice` still needs an explicit connect unless its subclass initiates one.
Do not override the helper's URL with an instrument address.

Important details of the inspected helper:

- Response dictionary keys are exact decoded commands without the separator;
  retain spaces, commas, and question-mark placement. Responses are encoded
  as ASCII with the configured separator appended.
- A non-`None` response is sent automatically. `None` means no mapped response;
  an empty string sends an empty reply frame, which is different from silence.
- Unmapped commands enter `server.queue`. Commands handled by the response
  map do not enter that queue; it is not a complete traffic log.
- `server.on_input(pattern, awaitable)` registers a one-shot side effect,
  used only when no non-`None` mapped response exists. The implementation
  awaits the supplied object; pass a coroutine object, not merely an async
  function. Ensure registered coroutine objects are consumed or closed.
- Use a fresh response dictionary per test. Mutating shared module-level maps
  can couple tests, as some existing examples do.
- The helper accepts one client connection and is not a full reconnect peer.
  Inspect its cleanup in the installed version: the inspected implementation
  cancels the listening server task but does not explicitly join every task
  and close every accepted transport. Ensure the device disconnects and
  explicitly clean additional test-owned resources. For reconnect or task
  cleanup contracts, use a fixture with complete ownership of the peer.

Use a dedicated small localhost peer when asserting byte encodings, different
request/reply separators, arbitrary frames, unsolicited streams, repeated
side effects, or the complete command/query sequence. Bind new peers to
`127.0.0.1` on port `0`; record requests before responding and bound all waits.

## Readback Example

For `ExampleSupply` from [device-patterns.md](device-patterns.md), saved as
the device module `ExampleSupply.py`, this test proves that a remote setting
sends the expected command and publishes the queried hardware value, even
when that differs from the requested value. Use the repository's existing
loop-policy fixture and loop-scope settings.

```python
from asyncio import wait_for

import pytest

from karabo.middlelayer import getDevice, setWait, waitUntil
from scpiml.tests.mock_hardware import mock_server

from ..ExampleSupply import ExampleSupply


@pytest.mark.timeout(30)
async def test_voltage_readback():
    responses = {"VOLT?": "1.0", "MEAS:VOLT?": "0.9"}
    async with mock_server(ExampleSupply, responses, b"\n") as (server, ctx):
        device = ctx["device"]
        with await getDevice(device.deviceId) as proxy:
            try:
                await proxy.connect()
                await wait_for(waitUntil(lambda: proxy.voltage == 1.0), 2)
                responses["VOLT?"] = "2.25"
                await setWait(proxy, voltage=2.5)
                assert await wait_for(server.queue.get(), 2) == "VOLT 2.5"
                await wait_for(waitUntil(lambda: proxy.voltage == 2.25), 2)
                assert proxy.voltage.value == pytest.approx(2.25)
            finally:
                await proxy.disconnect()
```

This demonstrates the helper's response map and command queue. It does not
assert every query or prove transport cleanup; use the dedicated peer for
those contracts. Under strict asyncio mode, also mark the async test using
the target repository's loop scope.

## Select Relevant Behaviors

Choose cases justified by the change, rather than implementing every row:

| Change | Observable checks |
| --- | --- |
| New aliased property or slot | Exact outgoing command, parsed result, access/state behavior |
| Connection configuration | Required initial queries/writes, unset value behavior, hardware-retention policy |
| Command reader/readback | Silence versus acknowledgement, accepted value versus queried value, no false success on rejection |
| Node addressing | Channel bytes at initialization, polling, and remote writes; correct owning property updated |
| Nested node | Deepest changed level, root and parent dispatch paths, custom reader/decoder placement |
| Parser or framing | Realistic normal/error replies, delimiters, fragmented input, EOF, timeout |
| Polling | Changed peer response eventually published, selected interval, stop on disconnection |
| Acquisition | Start/stop bytes, fragmented stream assembly, no competing reads, polling restored, owned task finishes |
| Reconnection | Successful reinitialization without duplicate polling/acquisition tasks |

Use `setWait` for remote setter semantics and a bounded proxy wait for
publication; setting `device.voltage = value` directly is not the same test.
Inspect `server.queue` or a peer log for commands instead of asserting that a
slot returned without error. Use events and bounded condition waits instead
of copying the example repositories' fixed sleeps. For nested changes, do
not rely solely on startup tests: startup dispatch can differ from setters.

## Run And Report

Run the focused tests, then affected package tests and configured lint checks.
Use the device repository's paths. When explicitly working on the framework,
its recorded checks are:

```sh
pytest src/scpiml/tests/scpi_test.py -q
pytest src/scpiml/tests/code_quality_test.py -q
pytest src/scpiml/tests -q
```

The framework fixture binds `127.0.0.1:35232`; run those tests serially. Do
not impose that fixed port on new downstream peers. These checks need the
Karabo test runtime and local sockets, not physical hardware. Report missing
runtime dependencies or socket restrictions separately from test failures.
