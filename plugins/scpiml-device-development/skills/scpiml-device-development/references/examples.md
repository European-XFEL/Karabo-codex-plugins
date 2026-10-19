# Source Examples And Compatibility Boundaries

These references were distilled from the scpiml framework and five downstream
repositories. Paths below are relative to each named repository; the skill
does not require those repositories at a particular filesystem location.
Use the bundled explanations when sources are unavailable. If an exact
implementation or instrument command is needed, obtain the source/manual
rather than guessing from a repository name.

## Framework: scpiml

Primary behavior source: `src/scpiml/scpi.py` (inspected at `ae9be30`).
Public exports: `src/scpiml/__init__.py`.

- `ScpiConfigurable.__init_subclass__` explains automatic alias wiring and
  why explicit decorated methods own their command calls.
- `sendCommand`, `sendQuery`, and `BaseScpiDevice.writeread` explain result
  publication, readback, dispatch context, locking, and shielding. Read these
  to understand behavior; do not override them in downstream drivers.
- `ScpiConfigurable.connect` defines connection writes/reads and poll setup;
  `decodeURL` and `open_connection` define actual supported transport syntax.
- `src/scpiml/tests/scpi_test.py` exercises initial writes/reads, command
  replies, custom framing, per-property formats, polling, and nodes.
  `test_nested_node` covers nested initialization; it is not proof that every
  deep remote setter path works with the same formatter.
- `src/scpiml/tests/mock_hardware.py` supplies downstream test infrastructure.

The documentation in `doc/source/general_device_implementation.md` and
`device_specific_implementation.md` provides a useful manual-to-schema
workflow. Check snippets against source and tests rather than treating them
as runnable templates.

## ScpiPowerSupplies: Shared Devices And Reply Variants

Inspect `src/ScpiPowerSupplies/ScpiPowerSupply.py`, `TDKPowerSupply.py`,
`FugPowerSupply.py`, `KepcoPowerSupply.py`, and `HeinzingerPowerSupply.py`.

- Shared `Voltage`/`Current` nodes separate requested and measured values;
  measured values poll while target values read on connection.
- The node tree groups the UI; the formatter emits leaf aliases directly.
- TDK overrides `readCommandResult` to return `value` without reading because
  its commands have no reply. This is the simplest no-reply pattern.
- FUG uses a command prefix, per-slot formats, prefixed reply parsing, and
  vendor error acknowledgements. It redeclares inherited aliased descriptors
  rather than assuming `Overwrite` will rewire their senders correctly.
- Kepco and Heinzinger show small vendor subclasses reusing the shared base.
- `follow_hardware_state` illustrates publishing instrument output state,
  including a connection-state choice through `initialConnectedState`.

Caveat: FUG's error reader returns `None`. In the inspected framework that
does not prevent the sent value from being published when readback is false.
Extract the acknowledgement-recognition idea, not a general error-return
convention. Test explicit failure behavior for the target device.

Tests live under `src/ScpiPowerSupplies/tests/`; the TDK and generic supply
tests show response-map peers and state/property checks. Avoid their shared
mutable response maps and timing sleeps in new tests.

## dg645: Compound Settings, Nested Nodes, Startup Policy

Inspect `src/dg645/Dg645.py`, `ChannelNodes.py`, and `tests/device_test.py`.

- Commands have no reply; `readCommandResult` returns `None` with
  `commandReadBack=True`, allowing a subsequent query to report actual values.
- Alias `DLAY 2` is transformed into channel-specific query/command syntax.
  Query placement and commas matter; generic `alias + '?'` is insufficient.
- `get_channel_delay_node` stages reference channel and delay, then its Apply
  slot sends the composite value in one command and passes the owning node.
- `NestedNode` supplies formatting for the prescaler hierarchy.
- `onConnect` chooses read versus write from the per-instance
  `isKeepHardwareSettings` policy, avoiding mutation of shared descriptors.
- Although the class derives from `ScpiDevice`, `onInitialization` connects.

Reuse these decisions, not every implementation detail. Some tests merely
invoke slots or use fixed sleeps; strengthen relevant tests with actual
command assertions and bounded waits when implementing new behavior.

## lakeshoreHeaterPy: Model Families And Multi-Value Replies

Inspect the middlelayer files `src/lakeshoreHeaterPy/LakeshoreHeaterMdl.py`,
`LakeshoreModel325Mdl.py`, `LakeshoreModel335Mdl.py`,
`LakeshoreModel336Mdl.py`, and `utils.py`.

- Node factories select channel schema according to model capabilities.
- Aliases such as `output1` or `inputA` determine the channel argument;
  commands use syntax such as `SETP 1,value`, queries `SETP? 1`.
- No-reply commands return the requested value without reading.
- `pidString` and related descriptors parse one composite reply into several
  properties. `slotReconfigure` assembles multi-input commands from changed
  and retained fields. Treat this as an existing specialized design, not a
  requirement to override reconfiguration in every scpiml device.

Compatibility caveats: the 335 example's `serial://` URL and `baudRate`/
`dataBits` options are not accepted by the inspected scpiml transport. The
325's `enableConnectionCheck` attribute has no corresponding behavior in
that framework. Verify inherited support before copying such settings.
The repository also contains bound-Python classes without the `Mdl` suffix;
do not mix their transport or lifecycle with scpiml.

The `tests/common.py` response builder and `lakeshore325_test.py`,
`lakeshore335_test.py`, and `lakeshore336_test.py` illustrate model-specific
initial readout. Startup coverage alone does not verify composite writes.

## energyMax: Handshakes, Acquisition, And Reader Ownership

Inspect `src/energyMax/EnergyMaxMDL.py`, `labMaxTMDL.py`,
`tests/energymax_device_test.py`, and `tests/labmaxt_device_test.py`.

- Both middlelayer classes derive from `ScpiDevice` but initiate connection
  in `onInitialization`; they choose `State.STOPPED` after connection.
- `parseResult` strips quoted responses, and custom readers handle handshake
  details. Query/command result handling must consume complete replies:
  converting `OK` to an empty frame is not universally correct.
- EnergyMax checks for actual hardware behind a serial-to-Ethernet bridge.
- Its acquisition mode disables polling and reads stream chunks, retaining
  incomplete records between chunks. On stop it cancels acquisition and
  restores polling. This motivates explicit stream ownership; its fixed
  startup delay is not a sufficient synchronization pattern to copy.
- LabMaxT shows explicit node queries through the root with `child=self`,
  and organization nodes whose names do not contribute SCPI prefixes.

`EnergyMax.py` is bound-Python; use `EnergyMaxMDL.py` for scpiml patterns.
The inspected EnergyMax device test explicitly lacks simulated measurement
streaming, so its start/stop assertions do not validate data acquisition.
Add real fragmented measurement input when working on that behavior.

## temBeamLock: Unsolicited Traffic As A Special Case

Inspect `src/temBeamLock/TemBeamLock.py` and `tests/device_test.py`.

- The protocol uses `alias= value` rather than ordinary SCPI syntax.
- One monitor consumes continuous unsolicited messages mixed with replies;
  alias correlation and pending acknowledgement/poll queues track responses.
- XON/XOFF messages describe instrument buffer availability; asynchronous
  acknowledgement timeouts are separate from immediate command completion.

This implementation overrides `sendCommand`/`sendQuery`, which conflicts
with the framework repository's current downstream-extension rules. Treat it
as evidence of a protocol requirement and an existing compatibility exception,
not permission to override transaction internals in a new device. Preserve
existing behavior during a focused fix; discuss framework support before
introducing an equivalent exception elsewhere. Test interleaved replies,
timeouts, flow-control behavior, and cleanup for any such work.
