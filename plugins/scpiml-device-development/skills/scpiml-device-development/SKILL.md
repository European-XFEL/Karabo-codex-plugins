---
name: scpiml-device-development
description: Create, extend, debug, and test Karabo middlelayer instrument devices using scpiml, including ScpiDevice, ScpiAutoDevice, ScpiConfigurable nodes, SCPI aliases, protocol hooks, and simulated hardware. Use for downstream scpiml drivers and SCPI-like socket or serial protocols implemented through scpiml. Requires karabo-device-development. Do not route generic SCPI clients, scpi-bound devices, or scpiml framework maintenance here.
---

# scpiML Device Development

## Required Companion Skill

The `karabo-device-development` plugin must also be installed and its skill
available. If missing, ask the user to install it before implementing a device;
do not substitute a partial Karabo guide or mock the missing runtime.

Use that skill's middlelayer reference alongside this skill. For Python test
work, also load its pytest reference. Keep general schema, lifecycle, task,
proxy, packaging, and testing guidance there; this skill adds scpiml behavior.

## Establish The Device Contract

1. Read repository instructions, the target class and base classes, packaging,
   nearby tests, and any existing protocol peer. Identify the scpiml dependency
   constraint and the implementation actually imported in the Karabo environment.
2. Obtain the relevant instrument command documentation and requested feature
   requirements. Establish exact command/query bytes, replies or absence of
   replies, terminators, encoding, channel addressing, units, and hardware
   limits. Ask for missing protocol facts rather than inventing commands.
3. Identify automatic versus explicit connection, startup values that may be
   written, values to retain from hardware, polling, and any streaming mode.
   For extensions, preserve the existing public schema and behavior unless the
   request changes them.
4. Read [device-patterns.md](references/device-patterns.md) for implementation
   and protocol debugging. Read [testing.md](references/testing.md) when adding
   or diagnosing tests. Consult [examples.md](references/examples.md) for
   concrete patterns and compatibility caveats from the source repositories.
5. Implement the smallest applicable change and test its observable protocol
   and property/state behavior. Prefer existing shared device classes when
   their protocol and schema match the target instrument.

Use the target scpiml implementation and its tests to resolve behavior. Example
drivers can target older releases, contain specialized workarounds, or include
both bound and middlelayer implementations. These bundled references describe
the inspected framework, not a guarantee about every scpiml version.

## Essential scpiml Rules

- Import the public classes from `scpiml`. Use `ScpiAutoDevice` for automatic
  connection, `ScpiDevice` for explicit connect/disconnect slots, and
  `ScpiConfigurable` for instrument nodes. Check subclass initialization:
  several example `ScpiDevice` classes explicitly connect on startup.
- An aliased descriptor without an explicit method/setter is wired to send a
  command. A decorated setter or slot owns its command call. Local assignment
  publishes a value; it is not equivalent to a remote property write.
- Add scpiml metadata after descriptor construction, for example
  `voltage.readOnConnect = True`. Keep instrument addresses in aliases and
  user-facing property names independent of protocol syntax.
- Prefer `command_format`, `query_format`, descriptor `commandFormat` and
  `queryFormat`, `createNodeCommand`, `createNodeQuery`, result readers,
  `parseResult`, and `scpi_data_encoder`/`scpi_data_decoder`. Use the root
  `readline` hook when framing requires it. Use `onConnect` for connection
  setup. Do not override scpiml descriptor wiring, child dispatch,
  `sendCommand`, `sendQuery`, or polling internals in new drivers.
- Call `sendCommand`/`sendQuery` from normal setters, slots, or connection
  hooks. Never call them from formatting or result-reader hooks. The root
  transaction lock and shielding protect write/reply pairing; do not nest a
  transaction under that lock or bypass it with independent writer calls.
- Default command handling consumes one reply line and returns the sent
  value. Instruments with no command reply need a result-reader override.
  `commandReadBack=True` issues a query only if the reader returns `None` and
  a value was sent. A returned value is published directly instead.
  `readOnCommand` is legacy; do not introduce it.
- `writeOnConnect` defaults to true for `INITONLY` descriptors: it sends a set
  value, or queries an unset one. `readOnConnect` is independent, so enabling
  both can issue an additional query. Read-only schema access alone does not
  protect against an explicitly enabled connection write.
- `poll=True` uses `pollingInterval`; a positive numeric `poll` gives seconds
  for that property. `polling_active=False` pauses future poll iterations; it
  does not cancel a read already in progress.
- Instrument nodes need aliases to participate in automatic connection and
  polling. Their hierarchy need not match SCPI addressing. Supply formatting
  at every node level that dispatches transactions, and verify both startup
  and remote-write paths for nested nodes.
- Use local simulated peers for routine validation. Connection itself can
  write settings. Do not replace a test URL with a real instrument endpoint
  without authorization for that hardware operation.

## Finish The Change

Run focused protocol/device tests and the package's configured checks in the
Karabo environment, following the companion skill. Report the behavior
implemented, verification performed, and any environment or hardware limits.
Do not broaden a downstream device task into a framework rewrite. If a
protocol cannot fit the supported hooks, explain the limitation and discuss
the necessary framework change instead of silently replacing transaction
internals.
