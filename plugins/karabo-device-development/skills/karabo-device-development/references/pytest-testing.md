# Karabo Pytest Development

Use this guide whenever adding, changing, reviewing, or diagnosing Python tests
in a Karabo repository. Combine it with the selected middlelayer or bound-Python
API guide. This is a testing workflow, not a coverage-only workflow: implement
the behavior the user requested, and use coverage data only when it helps find
meaningful missing behavior.

## Contents

- [Route The Request](#route-the-request)
- [Establish The Contract](#establish-the-contract)
- [Choose The Smallest Useful Test Layer](#choose-the-smallest-useful-test-layer)
- [Design Assertions Around Observable Behavior](#design-assertions-around-observable-behavior)
- [Configure Middlelayer Async Tests](#configure-middlelayer-async-tests)
- [Build Isolated Fixtures](#build-isolated-fixtures)
- [Test Pure Logic And Protocol Parsing](#test-pure-logic-and-protocol-parsing)
- [Test A Device Directly](#test-a-device-directly)
- [Test Multiple Devices With AsyncDeviceContext](#test-multiple-devices-with-asyncdevicecontext)
- [Use Proxies Only For Proxy Semantics](#use-proxies-only-for-proxy-semantics)
- [Observe Transient Property Changes](#observe-transient-property-changes)
- [Test A Real TCP Boundary](#test-a-real-tcp-boundary)
- [Test Failures, Cancellation, And Background Tasks](#test-failures-cancellation-and-background-tasks)
- [Test Pipelines](#test-pipelines)
- [Test Descriptors, Schemas, And Tables](#test-descriptors-schemas-and-tables)
- [Parameterize Boundaries And Error Cases](#parameterize-boundaries-and-error-cases)
- [Use Coverage As A Diagnostic](#use-coverage-as-a-diagnostic)
- [Validate In Expanding Rings](#validate-in-expanding-rings)
- [Avoid Fragile Test Patterns](#avoid-fragile-test-patterns)
- [Review Checklist](#review-checklist)

## Route The Request

Identify the user's intent before editing:

- For "write tests for this behavior," test that behavior and its necessary
  success, failure, state, and boundary cases. Do not start a repository-wide
  coverage campaign.
- For feature or bug-fix work, add a focused regression test that would fail
  without the requested behavior whenever practical.
- For a failing test, diagnose whether the production behavior, expectation,
  fixture isolation, lifecycle cleanup, or execution environment is wrong. Do
  not weaken the assertion merely to make the test pass.
- For "increase coverage," first establish a passing baseline, then use
  uncovered lines to locate candidate behaviors. Select cases with a stable,
  observable effect; do not write tests whose only value is executing a line.
- For a review request, inspect and report. Do not modify production code or
  tests unless the user also asks for changes.

Keep test-only work test-only. Change production code only when the user asks
for a fix or when the requested test cannot be written because of a confirmed
production defect; report that defect instead of silently broadening scope.

## Establish The Contract

Before writing a test, inspect:

1. Repository instructions and the selected Karabo API guide.
2. `pyproject.toml`, `pytest.ini`, or equivalent pytest, coverage, timeout,
   asyncio, formatter, and linter configuration.
3. The production path under test, including lifecycle and cleanup behavior.
4. The nearest test module, `conftest.py`, fake devices, mock controllers, and
   shared test helpers.
5. Public schema details such as access mode, assignment, allowed states,
   units, limits, and alarms when relevant.

Derive every expectation from production code, a public contract, a bug
report, or an established repository convention. Never invent an expected
command, status string, timeout, or state transition simply to fill a branch.

Write down the behavior as a small contract before implementing it:

```text
Given the controller rejects a move command,
when the device executes move(),
then the error is propagated, state becomes UNKNOWN,
status explains the controller failure, and reconnect is scheduled once.
```

That contract tells you what to stimulate and what to assert. It also exposes
when a proposed mock would replace the very logic the test is meant to cover.

Preserve the repository's layout, naming, import style, async policy, and
fixture conventions. Extend the clearly related test file unless a new layer
or a reusable fake justifies a separate module.

## Choose The Smallest Useful Test Layer

Select the lowest layer that can observe the promised behavior:

| Layer | Use it for | Typical tools |
| --- | --- | --- |
| Pure function or protocol unit | Parsing, formatting, validation, conversion, command selection | Plain pytest, parameterization |
| Descriptor or schema | Defaults, limits, access mode, units, options, table columns | Device class, descriptor/schema APIs |
| Direct device | Slot logic, state/status updates, local coordination, error mapping | Device instance plus fake external boundary |
| Multi-device runtime | Initialization, dependency discovery, device-to-device coordination | `AsyncDeviceContext` |
| Connected proxy | Remote writes, notifications, transient property changes, proxy errors | `getDevice`, `setWait`, `waitUntil`, `Queue` |
| Pipeline | Channel connection, data delivery, schema changes, end-of-stream | Sender/receiver devices and channels |
| Protocol peer | Wire commands, reconnects, framing, malformed replies | Localhost TCP/UDP server on an ephemeral port |
| Server subprocess | Real server startup, plugin discovery, server/device lifecycle | `AsyncServerContext` |

Prefer a pure or direct test when remote semantics are irrelevant. A smaller
test has fewer moving parts and usually diagnoses failures more clearly.

Use `AsyncServerContext` only when the behavior genuinely depends on a Karabo
server subprocess--for example, server-side plugin discovery or process
lifecycle. It invokes a real `karabo-<api>server`, requires the corresponding
runtime configuration, and is not a general replacement for
`AsyncDeviceContext`.

Do not mix middlelayer and bound-Python test machinery. For bound-Python
devices, follow the bound API guide and the repository's existing server/client
fixtures. Do not introduce `AsyncDeviceContext` unless the repository already
has an intentional interoperability test.

## Design Assertions Around Observable Behavior

Protect one coherent behavior per test. Assert results that users or
collaborators can observe:

- return values and raised exceptions;
- state, status, alarms, and public property values;
- emitted controller or protocol commands;
- data delivered through a pipeline and end-of-stream behavior;
- resource cleanup, reconnect scheduling, or task termination;
- remote errors and property notifications when proxy semantics matter.

It is fine for one behavior to require several related assertions. For
example, a failed hardware transaction may have to set `State.UNKNOWN`, expose
a useful status, close the connection, and schedule a reconnect. Avoid tests
that assert several unrelated features merely because they share a fixture.

Mock or fake external boundaries:

- hardware controller or transport objects;
- TCP peers and external services;
- clocks, backoff scheduling, and unavoidable infrastructure;
- collaborating devices when their real implementation is outside the test's
  contract.

Do not patch the method under test, replace the branch logic being tested, or
assert private helper calls solely to prove delegation. Prefer a stateful fake
that behaves like the external boundary and records meaningful interactions.

Assert stable error meaning rather than the complete representation of a
nested exception:

```python
with pytest.raises(KaraboError, match="controller rejected move"):
    await device.move()
```

For Karabo numeric values, compare `.value` when metadata or units are not part
of the behavior:

```python
assert device.position.value == pytest.approx(1.25)
```

Compare the complete quantity only when unit, metric prefix, timestamp, or
other metadata is explicitly under test.

## Configure Middlelayer Async Tests

Follow the local pytest-asyncio configuration. In current middlelayer suites,
make loop sharing explicit when module-scoped devices or network servers share
tasks:

```python
import pytest

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.timeout(30),
]
```

Match async fixture scope to loop scope:

```python
import pytest_asyncio


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def runtime():
    ...
```

If the repository uses `run_test` or configures a default loop scope, preserve
that established convention. Do not introduce both styles in one test module.

Do not create or override an `event_loop` fixture. If the repository genuinely
requires Karabo's loop policy and does not already configure it, use pytest-asyncio's policy fixture at the established scope:

```python
@pytest.fixture(scope="session")
def event_loop_policy():
    return KaraboTestLoopPolicy()
```

Use explicit, bounded waits. A module-level timeout is a useful final safety
net, but apply `asyncio.wait_for()` around waits for mock-peer IO, events,
queues, and task completion so failures point to the stalled operation.

## Build Isolated Fixtures

Choose fixture scope deliberately:

- Use function scope by default.
- Use module scope for expensive multi-device runtimes only when every mutable
  field, queue, task, connection, and fake response can be reset safely.
- Split expensive startup from per-test reset rather than letting tests depend
  on execution order.
- Generate unique device IDs with `create_instanceId()` when parallel runs or
  stale topology entries could collide.

`AsyncDeviceContext` starts all supplied devices, waits until they initialize,
provides access by the supplied labels, and shuts down devices and their local
servers on exit:

```python
import asyncio
from contextlib import suppress

import pytest
import pytest_asyncio

from karabo.middlelayer import State
from karabo.middlelayer.testing import AsyncDeviceContext, create_instanceId


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def runtime():
    motor_id = create_instanceId("FakeMotor")
    controller_id = create_instanceId("Controller")

    motor = FakeMotor({"_deviceId_": motor_id})
    controller = Controller({
        "_deviceId_": controller_id,
        "motorDeviceId": motor_id,
    })

    async with AsyncDeviceContext(motor=motor, controller=controller) as ctx:
        yield ctx


@pytest_asyncio.fixture
async def clean_runtime(runtime):
    motor = runtime["motor"]
    controller = runtime["controller"]

    # Arrange a known baseline for every test.
    motor.position = 0.0
    motor.state = State.ON
    controller.targetPosition = 0.0
    controller.state = State.ON
    controller.status = "Ready"
    yield runtime

    # Cancel or await test-created work before the next test starts.
    task = controller.move_task
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    controller.move_task = None
```

Do not rely on one test leaving a device in the state required by the next.
Avoid autouse reset fixtures unless every test truly needs them; explicit
fixtures make state dependencies easier to see.

## Test Pure Logic And Protocol Parsing

Keep pure protocol behavior outside a running Karabo topology when possible.
Parameterize representative normal and boundary values:

```python
import pytest

from pi_controller.protocol import ProtocolError, parse_axis_position


@pytest.mark.parametrize(
    ("reply", "axis", "expected"),
    [
        ("1=0.000000", 1, 0.0),
        ("2=-12.500000", 2, -12.5),
        ("3=1.25e-3", 3, 0.00125),
    ],
)
def test_parse_axis_position(reply, axis, expected):
    assert parse_axis_position(reply, axis) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        ("", "empty reply"),
        ("not-a-position", "malformed position"),
        ("2=4.2", "expected axis 1"),
    ],
)
def test_parse_axis_position_rejects_invalid_reply(reply, message):
    with pytest.raises(ProtocolError, match=message):
        parse_axis_position(reply, axis=1)
```

The cases document valid syntax, numerical conversion, axis correlation, and
error meaning. They are better than several tests that each execute one parser
line without protecting a distinct rule.

## Test A Device Directly

Use a direct device test for local slot logic, state changes, and interaction
with a replaceable hardware boundary. Give the fake behavior, synchronization
points, and recorded calls instead of a forest of patched methods:

```python
import asyncio

import pytest

from karabo.middlelayer import State


class FakeController:
    def __init__(self):
        self.accept_move = asyncio.Event()
        self.move_started = asyncio.Event()
        self.commands = []
        self.position = 0.0

    async def move(self, axis, target):
        self.commands.append(("move", axis, target))
        self.move_started.set()
        await self.accept_move.wait()
        self.position = target

    async def read_position(self, axis):
        return self.position


async def test_move_updates_state_and_position(axis_device):
    fake = FakeController()
    axis_device.controller = fake
    axis_device.targetPosition = 2.5

    task = asyncio.create_task(axis_device.move())
    await asyncio.wait_for(fake.move_started.wait(), timeout=1)

    assert axis_device.state == State.MOVING
    assert fake.commands == [("move", axis_device.axis.value, 2.5)]

    fake.accept_move.set()
    await asyncio.wait_for(task, timeout=1)

    assert axis_device.position.value == pytest.approx(2.5)
    assert axis_device.state == State.ON
```

The events make the intermediate-state assertion deterministic. A fixed sleep
would only guess when the task had reached the hardware call.

## Test Multiple Devices With AsyncDeviceContext

Use a shared runtime when initialization or coordination between real test
devices is part of the behavior. Keep assertions direct if networked proxy
semantics are not part of the contract:

```python
async def test_interlock_blocks_motion(clean_runtime):
    interlock = clean_runtime["interlock"]
    motor = clean_runtime["motor"]
    controller = clean_runtime["controller"]

    interlock.isSafe = False
    controller.targetPosition = 4.0

    with pytest.raises(KaraboError, match="interlock is not safe"):
        await controller.move()

    assert motor.move_calls == []
    assert controller.state == State.ERROR
    assert "interlock" in controller.status.lower()
```

Initialization may perform asynchronous discovery. Wait for a real readiness
condition rather than sleeping:

```python
from karabo.middlelayer.testing import sleepUntil


await sleepUntil(
    lambda: controller.connectedToMotor.value,
    timeout=5,
)
```

Use `sleepUntil` for local/direct objects when no proxy notification drives the
condition. It polls every short interval and supports a timeout.

## Use Proxies Only For Proxy Semantics

Connect a proxy when the test must prove remote writes, slot invocation,
notifications, allowed-state enforcement, or remote error propagation:

```python
import pytest

from karabo.middlelayer import State, getDevice, setWait, waitUntil


async def test_remote_move_publishes_final_position(runtime):
    device_id = runtime["axis"].deviceId

    with await getDevice(device_id) as axis:
        await setWait(axis, targetPosition=7.5)
        await axis.move()
        await waitUntil(lambda: axis.state == State.ON)

        assert axis.position.value == pytest.approx(7.5)
        assert axis.status == "Ready"
```

`setWait` confirms that a remote write has been processed. `waitUntil` reacts
to changes from connected proxies and is preferable to polling or fixed
sleeps. If the awaited call itself guarantees that the final state is already
established, assert immediately; an unnecessary wait can hide ordering bugs.

Use `waitUntilNew` when any new update is the behavior being tested:

```python
import asyncio

from karabo.middlelayer import waitUntilNew


await asyncio.wait_for(waitUntilNew(axis.status), timeout=3)
assert "reconnected" in axis.status.lower()
```

`waitUntil` and `waitUntilNew` require the referenced proxy to remain connected
while waiting. They do not take a timeout themselves in all supported Karabo
versions, so bound them with `asyncio.wait_for()` or the repository's pytest
timeout convention.

## Observe Transient Property Changes

A final-value assertion cannot prove that a brief transition occurred. Attach
a `Queue` before triggering the action to capture every proxy property update:

```python
import asyncio

from karabo.middlelayer import Queue, State, getDevice, waitUntil


async def test_move_publishes_moving_before_on(runtime):
    with await getDevice(runtime["axis"].deviceId) as axis:
        changes = Queue(axis.state)
        try:
            await axis.move()
            first = await asyncio.wait_for(changes.get(), timeout=2)
            assert first == State.MOVING

            await waitUntil(lambda: axis.state != State.MOVING)
            assert axis.state == State.ON
        finally:
            # Queue unregisters when released.
            del changes
```

If unrelated state changes are permitted, consume until the specific expected
transition while rejecting forbidden ones and retaining a timeout:

```python
while True:
    state = await asyncio.wait_for(changes.get(), timeout=2)
    assert state != State.ERROR
    if state == State.MOVING:
        break
```

Create the queue before the action; creating it afterward can miss a fast
transition and turn a correct implementation into a hanging test.

## Test A Real TCP Boundary

Use a localhost protocol peer when framing, command text, connection handling,
or reconnect behavior is the contract. Bind port `0` to avoid collisions and
read the selected port from the socket:

```python
import asyncio
from contextlib import suppress

import pytest_asyncio


class ProtocolPeer:
    def __init__(self):
        self.connected = asyncio.Event()
        self.reader = None
        self.writer = None

    async def accept(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.connected.set()
        await writer.wait_closed()

    async def receive_line(self):
        data = await asyncio.wait_for(self.reader.readline(), timeout=2)
        return data.decode("ascii").rstrip("\r\n")

    async def reply(self, text):
        self.writer.write(f"{text}\n".encode("ascii"))
        await asyncio.wait_for(self.writer.drain(), timeout=2)

    async def close(self):
        if self.writer is not None:
            self.writer.close()
            with suppress(ConnectionError, asyncio.TimeoutError):
                await asyncio.wait_for(self.writer.wait_closed(), timeout=2)


@pytest_asyncio.fixture
async def protocol_peer():
    peer = ProtocolPeer()
    server = await asyncio.start_server(peer.accept, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield peer, f"tcp://127.0.0.1:{port}"
    finally:
        await peer.close()
        server.close()
        await asyncio.wait_for(server.wait_closed(), timeout=2)
```

Drive both sides and assert the real wire contract:

```python
async def test_position_query_uses_axis_and_parses_reply(protocol_peer):
    peer, endpoint = protocol_peer
    device = ControllerDevice({
        "_deviceId_": create_instanceId("Controller"),
        "endpoint": endpoint,
        "axis": 2,
    })

    async with AsyncDeviceContext(device=device):
        await asyncio.wait_for(peer.connected.wait(), timeout=2)

        query = asyncio.create_task(device.readPosition())
        assert await peer.receive_line() == "POS? 2"
        await peer.reply("2=12.5000")
        await asyncio.wait_for(query, timeout=2)

        assert device.position.value == pytest.approx(12.5)
```

Keep protocol peers function-scoped unless reset and connection lifecycle are
proven safe. Close accepted writers as well as the listening server. Add tests
for malformed replies, EOF, timeout, and reconnect only when those are real
device promises.

## Test Failures, Cancellation, And Background Tasks

Failure tests should assert the complete public outcome, not only that an
exception occurred:

```python
async def test_transport_failure_marks_unknown_and_schedules_reconnect(axis):
    axis.controller.transact.side_effect = OSError("connection reset")

    with pytest.raises(OSError, match="connection reset"):
        await axis.updatePosition()

    assert axis.state == State.UNKNOWN
    assert "connection reset" in axis.status
    assert axis.controller.is_connected is False
    assert axis.reconnect_scheduled is True
```

Patch the external transaction or scheduling boundary, not
`axis.updatePosition()` itself. If reconnect timing would make the test slow,
replace the scheduler with a recording fake and assert the requested delay and
callback.

For cancellation, synchronize at a meaningful point, cancel, await the task,
and assert cleanup:

```python
async def test_cancel_move_stops_polling_and_clears_task(axis):
    polling = asyncio.Event()
    axis.controller.polling = polling

    task = asyncio.create_task(axis.move())
    await asyncio.wait_for(polling.wait(), timeout=1)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert axis.move_task is None
    assert axis.controller.pending_request is None
    assert axis.state != State.MOVING
```

Never leave a task running after a test. In fixture teardown, cancel and await
tasks under `suppress(asyncio.CancelledError)`. Verify that fake transports,
proxies, servers, queues, and writers are also released.

## Test Pipelines

Pipeline tests must prove delivery, not just connection configuration. Build a
small sender and receiver or reuse established repository helpers. Configure
the receiver with the sender's full channel ID:

```python
source_id = create_instanceId("Source")
sink_id = create_instanceId("Sink")

source = SampleSource({"_deviceId_": source_id})
sink = SampleSink({
    "_deviceId_": sink_id,
    "input": {
        "connectedOutputChannels": [f"{source_id}:output"],
    },
})

async with AsyncDeviceContext(source=source, sink=sink):
    assert sink.received.value == 0

    source.output.schema.sequence = 41
    source.output.schema.value = 3.5
    await source.output.writeData()

    await waitUntil(lambda: sink.received.value == 1)
    assert sink.lastSequence.value == 41
    assert sink.lastValue.value == pytest.approx(3.5)

    await source.output.writeEndOfStream()
    await waitUntil(lambda: sink.sawEndOfStream.value)
```

The receiver used by the example would expose explicit observable fields from
its handlers:

```python
class SampleSink(Device):
    received = UInt32(defaultValue=0)
    lastSequence = UInt32(defaultValue=0)
    lastValue = Double(defaultValue=0.0)
    sawEndOfStream = Bool(defaultValue=False)

    @InputChannel(raw=False)
    async def input(self, data, meta):
        self.received = self.received.value + 1
        self.lastSequence = data.sequence
        self.lastValue = data.value

    @input.endOfStream
    async def input(self, channel):
        self.sawEndOfStream = True
```

Adapt handler signatures and channel schema construction to the repository's
supported Karabo version. Test reconnect or schema replacement only when the
production device promises those behaviors. Use a real output/input pair for
delivery semantics; calling the receiver handler directly is only a unit test
of handler logic.

## Test Descriptors, Schemas, And Tables

Test schema contracts directly when the defect or feature concerns
configuration rather than runtime behavior. Useful assertions include:

- default values and assignment requirements;
- read-only versus reconfigurable access;
- allowed states and options;
- min/max limits, units, and metric prefixes;
- table row schema, column order, and validation;
- dynamically injected or overwritten properties.

Keep these assertions focused. Do not snapshot an entire schema for a one-field
contract; unrelated schema additions would create noisy failures.

Example for a table validation rule:

```python
def test_axis_table_rejects_duplicate_axis_numbers(device):
    rows = [
        {"name": "x", "axis": 1, "enabled": True},
        {"name": "y", "axis": 1, "enabled": True},
    ]

    with pytest.raises(ValueError, match="axis numbers must be unique"):
        device.axisConfiguration = rows
```

If validation occurs only through remote configuration, move the test to the
proxy layer and use `setWait`; do not force a direct assignment to represent a
contract it bypasses.

## Parameterize Boundaries And Error Cases

Use parameterization when the same rule applies to a meaningful set of inputs.
Good candidates include:

- lower, interior, and upper hardware limits;
- signed, scientific, and zero protocol values;
- each documented controller error code;
- state-dependent slot rejection;
- empty, partial, malformed, and unexpected replies;
- configuration with one, several, and duplicate channel or axis entries.

Name complex cases so failure output explains the scenario:

```python
@pytest.mark.parametrize(
    ("state", "allowed"),
    [
        pytest.param(State.ON, True, id="ready"),
        pytest.param(State.MOVING, False, id="already-moving"),
        pytest.param(State.ERROR, False, id="error-state"),
    ],
)
async def test_move_allowed_states(axis, state, allowed):
    axis.state = state
    if allowed:
        await axis.move()
    else:
        with pytest.raises(KaraboError, match="move is not allowed"):
            await axis.move()
```

Do not parameterize unrelated behaviors into one dense test. Separate success
and error paths when their setup and assertions differ materially.

## Use Coverage As A Diagnostic

Coverage is evidence about execution, not proof of correctness. Use the
repository's configured coverage command and request coverage.py JSON output.
Do not install a new test stack, rewrite test configuration, or add a coverage
threshold without authorization.

For explicit coverage work:

1. Run the configured suite and save a passing baseline report.
2. Group uncovered lines by surrounding class or function.
3. Inspect each candidate's production contract and existing tests.
4. Select meaningful error, state, boundary, protocol, or lifecycle behavior.
5. Add focused tests and run them first.
6. Rerun the same coverage command and compare like with like.

To group uncovered Python lines, use the skill helper:

```text
python <skill-root>/scripts/analyze_coverage.py \
  --repo-root <repo-root> \
  --coverage-json <coverage.json> \
  --output <analysis.json>
```

The output contains candidates, not recommendations. Reject:

- module-import plumbing and generated code;
- unreachable defensive branches;
- framework delegation with no repository-owned behavior;
- private implementation details without a stable observable effect;
- cases that require reproducing Karabo internals in the test.

Compare baseline and final reports with:

```text
python <skill-root>/scripts/compare_coverage.py \
  <before-coverage.json> <after-coverage.json>
```

Coverage comparison is mandatory only when coverage improvement is the
requested outcome. Do not require a percentage increase for a specifically
requested regression test, and do not add weak tests merely to reach a round
number.

## Validate In Expanding Rings

Use the active Karabo environment and the repository's own command choices.
Run validation in expanding rings:

```text
# One new behavior
pytest path/to/test_device.py::test_transport_failure -q

# The changed module
pytest path/to/test_device.py -q

# Closely related device or package tests
pytest path/to/tests -q

# Broader configured suite, when proportional to the risk
pytest -q
```

Then run the configured formatter, linter, and type checker for changed files.
Do not impose `autopep8`, `isort`, `flake8`, or another tool when the repository
uses a different stack.

For coverage tasks, rerun the exact baseline coverage command. Report:

- the behavior protected;
- focused and broader test results;
- before/after coverage measured on the same source and test selection;
- any environment limitation or untested risk.

Keep a change only when its required tests pass. Treat task leaks, unclosed
transports, timeout warnings, and lint failures as real failures.

## Avoid Fragile Test Patterns

Do not:

- use fixed sleeps to guess when async work has completed;
- catch broad exceptions and continue;
- add retries, skips, or relaxed assertions to conceal instability;
- patch the method or condition being tested;
- assert only that a mock was called when a public result exists;
- depend on test ordering or shared dirty device state;
- use fixed ports or non-unique device IDs;
- leave background tasks, proxies, queues, writers, or servers open;
- use `connectDevice` or a server subprocess for purely local behavior;
- copy middlelayer fixtures into bound-Python tests;
- assert complete exception text when a stable semantic substring suffices;
- make a coverage-only test that protects no meaningful behavior;
- rewrite an entire test module when a focused addition is sufficient.

Prefer deterministic synchronization:

| Need | Use |
| --- | --- |
| Fake reached a precise step | `asyncio.Event` |
| Local/direct condition became true | bounded `sleepUntil` |
| Connected proxy condition became true | `waitUntil` plus outer timeout |
| Any new proxy update | `waitUntilNew` plus outer timeout |
| Every transient property update | `Queue` plus `asyncio.wait_for` |
| Task or peer operation completed | `asyncio.wait_for` or `asyncio.timeout` |

## Review Checklist

Before handing off a test change, verify:

- [ ] The test matches the user's requested behavior and chosen API.
- [ ] Every expected value comes from a real contract.
- [ ] The smallest useful test layer is used.
- [ ] Assertions cover observable success or failure outcomes.
- [ ] External dependencies are faked at their boundary.
- [ ] Async loop scope matches fixture scope and repository convention.
- [ ] Transitions are synchronized with events, waits, or queues--not sleeps.
- [ ] Every wait and external IO operation is bounded.
- [ ] Device IDs and network ports cannot collide.
- [ ] Mutable fixture state is reset for each test.
- [ ] Tasks, contexts, proxies, queues, and transports are cleaned up.
- [ ] The focused test and proportionate broader suite pass.
- [ ] Coverage is compared only when coverage improvement was requested.
- [ ] The final report describes behavior, validation, and limitations--not only
      line coverage.
