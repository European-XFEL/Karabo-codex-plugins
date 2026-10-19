# Device Patterns And Protocol Decisions

## Contents

- [Minimal device](#minimal-device)
- [Command replies and readback](#command-replies-and-readback)
- [Nodes and explicit commands](#nodes-and-explicit-commands)
- [Parsing and framing](#parsing-and-framing)
- [Connection and acquisition lifecycle](#connection-and-acquisition-lifecycle)
- [Debugging by symptom](#debugging-by-symptom)

## Minimal Device

This illustrative instrument replies to queries, sends no command replies,
uses LF endings, and supports `VOLT`, `MEAS:VOLT`, and `*RST`. Replace protocol
facts with those from the instrument manual. Do not assume these commands or
the reset behavior exist on another instrument.

```python
from karabo.middlelayer import AccessMode, Double, Slot, State, Unit
from scpiml import ScpiDevice


class ExampleSupply(ScpiDevice):
    voltage = Double(
        alias="VOLT",
        displayedName="Target Voltage",
        unitSymbol=Unit.VOLT,
        allowedStates={State.NORMAL})
    voltage.readOnConnect = True
    voltage.commandReadBack = True

    actualVoltage = Double(
        alias="MEAS:VOLT",
        displayedName="Actual Voltage",
        unitSymbol=Unit.VOLT,
        accessMode=AccessMode.READONLY)
    actualVoltage.poll = True

    reset = Slot(
        alias="*RST",
        displayedName="Reset Instrument",
        allowedStates={State.NORMAL})
    reset.commandFormat = "{alias}\n"

    async def readCommandResult(self, descriptor, value=None):
        return None

    async def onDestruction(self):
        await self.close_connection()
```

`voltage` is read on connection and after a remote write. `actualVoltage` is
polled. A slot sends no value, so `reset` does not trigger automatic readback.
The default slot command format otherwise includes a space before the newline;
override it when the instrument requires an exact command without that space.
Add supported ranges, options, access levels, and state gates from requirements.

Use the device repository's entry-point layout. The downstream device needs a
`karabo.middlelayer_device` entry point and an appropriate scpiml dependency;
the scpiml library itself supplies no device-server entry point. Match the
repository's dependency/version conventions and leave generated `_version.py`
to setuptools-scm. Do not copy an example's old dependency pin blindly.

## Command Replies And Readback

Determine the reply contract before choosing an override:

| Instrument behavior | `readCommandResult` behavior | Property result |
| --- | --- | --- |
| One acknowledgement line; trust sent value | Consume/validate acknowledgement, return `value` | Sent value |
| No reply; trust sent value | Return `value` without reading | Sent value |
| No reply; query actual value after setting | Return `None`; enable `commandReadBack` | Follow-up query result |
| Acknowledgement followed by readback query | Consume/validate acknowledgement, return `None`; enable readback | Follow-up query result |
| Reply contains the resulting property value | Read and parse reply, return parsed value | Parsed reply; no extra query |

The default reader discards one line without validating its contents. Override
it when an acknowledgement can indicate failure. Returning `None` is not a
failure signal: with readback disabled, a non-`None` sent value is still
published; with readback enabled it triggers a query. Reject a negative
acknowledgement by the device's established error path before returning a
success value. Test that the property does not falsely report success.

Consume exactly the bytes belonging to the transaction. Leaving an `OK` or
error reply unread lets the next query consume the wrong response. Reading a
nonexistent acknowledgement causes a timeout, or an indefinite wait with a
negative timeout. Never send another command/query inside a result reader.

## Nodes And Explicit Commands

For one level of colon-addressed channels, a root device can use:

```python
from karabo.middlelayer import Double, KaraboValue, Node, Unit
from scpiml import ScpiConfigurable, ScpiDevice


class Channel(ScpiConfigurable):
    voltage = Double(alias="VOLT", unitSymbol=Unit.VOLT)
    voltage.readOnConnect = True


class ChannelSupply(ScpiDevice):
    channel1 = Node(Channel, alias="SOUR1")

    def createNodeQuery(self, leaf, node):
        return f"{node.alias}:{leaf.alias}?\n"

    def createNodeCommand(self, leaf, value, node):
        if isinstance(value, KaraboValue):
            value = value.value
        if value is None:
            return f"{node.alias}:{leaf.alias}\n"
        return f"{node.alias}:{leaf.alias} {value}\n"

    async def readCommandResult(self, descriptor, value=None):
        return value

    async def onDestruction(self):
        await self.close_connection()
```

This numeric example sends `SOUR1:VOLT 2.5\n` and queries
`SOUR1:VOLT?\n`. Normalize `KaraboValue` before formatting so units do not leak
into the command. For booleans, strings, vectors, quoting, and unit scaling,
implement the instrument's exact serialization; this numeric formatter is not
a universal serializer. The root default formatter converts through the
descriptor and Karabo's string conversion. Custom node formatters must honor
any per-descriptor formatting they intend to support.

Some nodes group UI properties only. In that case, formatting can use the
leaf alias without a node prefix (power supplies, EnergyMax), or place a
channel argument after the command (Lakeshore, DG645). Do not manufacture a
colon hierarchy from the Karabo node tree.

For nested nodes, trace the actual caller. Automatic setters send through the
root with the leaf's owning instance as `child`; initialization and polling
can dispatch through the parent node. Put compatible formatting and reply
handling on all relevant callers, using a small shared protocol base where
appropriate. A root-only override does not automatically apply to a node's
own `sendCommand` call. The framework's `test_nested_node` is useful evidence
for startup; also test remote writes and slots at the deepest changed level.
`commandReadBack` likewise defaults from the calling instance; a flag on a
node class does not control a root-dispatched write. Set the descriptor flag
when that property's policy must hold across dispatch paths.

For a custom setter or slot, explicitly call the desired transaction. An
aliased decorated method is not automatically wired. A slot descriptor can
be obtained as `type(self).reset`; a property value carries its descriptor.
Inside a node, prefer `self.get_root().sendCommand(descriptor, value,
child=self)` when the root owns formatting and reply handling. Passing the
owning node is necessary for correct addressing and property publication.
Do not perform this dispatch from a parser or descriptor publication callback.

For commands containing multiple values, keep the complete instrument command
together. Local staging properties plus an explicit Apply slot are suitable
when users must choose several fields before sending. DG645 illustrates this
pattern. When extending an existing combined-reconfiguration design such as
Lakeshore, preserve omitted values and validate the whole command; do not
invent one independent SCPI write per field.

Aliased inherited descriptors have already been wired by scpiml. Inspect and
test the generated setter before using `Overwrite` to change their protocol
metadata. The power-supply examples redeclare affected SCPI descriptors.
Ordinary non-SCPI settings such as `pollingInterval` can use normal Karabo
`Overwrite`. Do not mutate class descriptors per instance to choose a startup
policy: that also changes other instances sharing the class.

## Parsing And Framing

Choose the narrowest hook that changes the required behavior:

| Need | Mechanism |
| --- | --- |
| Different command/query text | Class formats or descriptor format attributes |
| Channel addressing | `createNodeCommand` / `createNodeQuery` |
| One property's text conversion | Descriptor `fromstring` |
| Common prefixes, quoted values, vendor numeric representations | `parseResult(descriptor, line)` |
| Multiple reply lines or handshaking | `readQueryResult` / `readCommandResult` |
| Different frame boundary | Root `readline()` returning bytes |
| Different bytes/text representation | `scpi_data_encoder` / `scpi_data_decoder` |

Default queries read one line, decode ASCII strictly, then call
`descriptor.fromstring` through `parseResult`. Empty decoded input returns
`None`; it is not automatically retried. Commands encode UTF-8. The encoder
runs on the root, while decoding/parsing uses the instance handling the query.
Preserve that distinction for nested-node protocols.

Default `readline` strips LF, CR, CRLF, or NUL endings and uses `timeout`;
negative means no deadline. A framing override must deliberately preserve
timeout, EOF, and cancellation behavior. A custom frame delimiter does not
by itself require a custom decoder. Avoid silently discarding invalid bytes
unless the instrument protocol explicitly requires that tolerance.

When one response updates several properties, parse it once and publish the
derived fields. Existing examples attach descriptor `__set__` callbacks for
this; retain established semantics when extending them. Such callbacks must
not recursively initiate hardware transactions. Pure parsing helpers make
compound replies easier to validate independently.

## Connection And Acquisition Lifecycle

- Current transports accept `socket://hostname:port/` or
  `file:///dev/ttyUSB0?speed=57600&bits=7&stopbits=1&parity=odd`. Serial
  options come from `decodeURL`; do not substitute `serial://`, `baudRate`,
  or `dataBits` from an unrelated library. Validate against the target version.
- `ScpiAutoDevice` starts connection in the background after `_run` and closes
  it in `onDestruction`. Do not add another startup connection. `ScpiDevice`
  supplies explicit slots; subclasses may intentionally connect during
  `onInitialization`. Inspect that choice rather than inferring it from the
  base-class name alone.
- `onConnect` runs after the transport opens and before that configurable's
  automatic descriptor initialization. Root `onConnect` runs before child
  nodes have completed their connection setup. Use it for ordered handshakes
  and conditional restore-versus-read decisions, avoiding duplicate writes
  from automatic flags.
- `connected=True` means the transport opened; it does not prove successful
  protocol initialization. A serial-to-Ethernet bridge can accept a socket
  while its instrument is absent. Verify an expected protocol response when
  the device requires that distinction.
- The base sets `initialConnectedState` after connection initialization;
  default is `State.NORMAL`. Choose a device-specific final state explicitly
  when needed. Poll tasks start during initialization and need not have all
  delivered their first value when that final state is assigned.
- Closing cancels framework polling and closes the writer. Preserve the
  production avoidance of `writer.wait_closed()`. Device-owned acquisition
  tasks need their own bounded cleanup. Preserve superclass destruction for
  automatic devices; for explicit devices ensure destruction closes an open
  connection as well as the public disconnect path.
- `polling_active` pauses polling, not all command traffic. Streaming needs
  one clear owner of the input stream. Before handing reads to an acquisition
  task, let in-flight transactions finish and prevent competing queries.
  On stop, terminate acquisition, join its reader task, handle residual data
  according to protocol, and restore polling. A fixed sleep alone does not
  establish exclusive ownership. Do not await an acquisition task from itself.
- For unsolicited replies mixed with command responses, require explicit
  correlation, timeout handling, and task ownership. BeamLock demonstrates
  why this needs special design; its internal overrides are not a template
  for new drivers. Discuss framework support if public hooks are insufficient.

## Debugging By Symptom

| Symptom | Inspect first |
| --- | --- |
| Every write times out | Reader waiting for an acknowledgement the instrument never sends |
| Next query receives `OK` or a stale value | Unconsumed reply, extra read, or competing reader |
| Readback flag seems ignored | Command reader returned a value instead of `None` |
| Decorated slot/setter sends nothing | Missing explicit transaction call; disconnected device |
| Nested values fail only at startup or polling | Parent-node formatter/reader differs from root path |
| Wrong units appear in command text | Raw `KaraboValue` interpolated in a custom formatter |
| Values unexpectedly change on reconnect | `INITONLY` default writes, explicit flags, `onConnect` policy |
| Transport connects but values never arrive | Bridge without instrument, wrong framing, wrong query syntax |
| Acquisition corrupts queries | Two consumers of the same stream or unfinished polling read |

Reproduce the relevant bytes with a simulated peer, then change the smallest
responsible hook. Report framework limitations separately from driver fixes.
