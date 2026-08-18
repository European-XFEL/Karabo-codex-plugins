# AGENTS.macro.md

This guide defines the policy and synchronous or asynchronous execution model
for Karabo macros and short interactive iKarabo procedures.

A macro uses middlelayer descriptors, values, proxies, remote calls, locks,
waits, topology, pipelines, and history. Do not duplicate those shared API
contracts here. For every macro task, read this file and `AGENTS.middlelayer.md`
completely.

## Table Of Contents

1. When To Use This Guide
2. Macro Or Middlelayer Device
3. Core Mental Model
4. Macro Syntax And Skeletons
5. Properties And Public Surface
6. Macro Slots, State, And Cancellation
7. Remote Devices And Proxy Scope
8. Remote Writes, Calls, And Locks
9. Bounded Waiting And Monitoring
10. Pipeline Snapshots
11. Topology Access
12. History
13. iKarabo
14. Development And Execution
15. Error Handling And Cleanup
16. Testing
17. Common Mistakes
18. Recommended Default Architecture

## 1. When To Use This Guide

Use this file for Karabo code that:

- subclasses `karabo.middlelayer.Macro` or `TopologyMacro`
- defines actions with `@MacroSlot(...)`
- uses macro helpers such as `RemoteDevice(...)` or `@Monitor()`
- is stored as a project macro and executed by a macro server
- is intended as a short iKarabo command or procedure

Always read this guide and `AGENTS.middlelayer.md` completely. Use the
middlelayer guide as the source of truth for shared feature behavior,
then apply the macro policy and syntax rules in this file. Do not route an
ordinary `karabo.middlelayer.Device` here merely because it controls remote
devices.

## 2. Macro Or Middlelayer Device

Choose a macro for a short, bounded, procedural task such as:

- a recurring beamtime- or experiment-specific automation
- a small specialization of an iKarabo workflow
- a prototype of a control procedure
- a bounded sequence of reads, writes, and slot calls on remote devices

Choose a middlelayer device when behavior needs any of the following:

- continuous or indefinite monitoring
- a custom state machine beyond automatic `ACTIVE` and `PASSIVE`
- persistent grouping or aggregation of devices
- distribution of properties or pipeline data
- a service that other devices or macros should control
- direct hardware communication
- complex branching, long-running loops, or an architecture likely to grow

Treat a macro as procedural orchestration with a limited lifetime. If the
implementation starts accumulating device-like responsibilities, migrate it
to a middlelayer device.

## 3. Core Mental Model

- A macro is a specialized middlelayer device executed on a macro server.
- Macro source belongs to a Karabo project configuration rather than a normal
  device package.
- Only one instance of a given macro class may run in one Karabo domain.
- `MacroSlot` supports both synchronous functions and coroutine functions.
- Choose async syntax when the user requests it or the existing macro already
  uses it; otherwise default to sync syntax.
- Public actions are exposed as GUI buttons and run under automatic macro
  state and cancellation handling.
- Remote hardware is controlled through Karabo proxies, never through direct
  hardware protocols.
- Macro execution must be bounded. Waiting for an operation is valid;
  permanent monitoring is not.

## 4. Macro Syntax And Skeletons

Choose the macro authoring style in this order:

1. Honor an explicit request for asynchronous macro syntax.
2. Match asynchronous syntax already present in the macro being changed.
3. Otherwise use synchronous syntax by default so the macro remains
   approachable for users who do not know `async`/`await`.

Use this synchronous baseline:

```python
from karabo.middlelayer import (
    Macro, MacroSlot, State, String, getDevice, setWait, waitUntil)


class MoveMacro(Macro):
    motorId = String(displayedName="Motor", defaultValue="motor/1")

    @MacroSlot(displayedName="Execute")
    def execute(self):
        with getDevice(self.motorId.value) as motor:
            setWait(motor, targetPosition=10.0)
            motor.start()
            waitUntil(lambda: motor.state == State.MOVING)
```

Call synchronized Karabo operations directly and use normal `with` contexts.

When async is explicitly requested or already established, use this form:

```python
from karabo.middlelayer import (
    Macro, MacroSlot, State, String, getDevice, setWait, waitUntil)


class MoveMacro(Macro):
    motorId = String(displayedName="Motor", defaultValue="motor/1")

    @MacroSlot(displayedName="Execute")
    async def execute(self):
        async with getDevice(self.motorId.value) as motor:
            await setWait(motor, targetPosition=10.0)
            await motor.start()
            await waitUntil(lambda: motor.state == State.MOVING)
```

In async macro code, await synchronized Karabo operations such as
`connectDevice(...)`, `setWait(...)`, remote slots, waiting helpers, and
`sleep(...)`; for example, use `motor = await connectDevice(...)`. Use
`async with` when the returned proxy context supports it.

Do not rewrite an existing async macro into sync syntax merely because sync is
the default. Keep the macro internally consistent.

After finishing a synchronous macro implementation, ask once whether the user
wants it converted to async syntax. If the user accepts, update the given
codebase to async. If the user declines or has already declined, never ask
again. Do not repeat an unanswered offer in the same task or conversation.

The middlelayer guide often shows the same shared operation in asynchronous
device code. Preserve its API semantics, lifetime rules, acknowledgement
rules, and error behavior while using the macro syntax selected above.

Keep the main action readable as a short procedure. Extract calculations and
reusable internal behavior into ordinary `snake_case` helper functions.

## 5. Properties And Public Surface

Read the middlelayer guide sections on class and schema assembly, descriptors,
naming, nodes and tables, property values, and timestamps. Those contracts
also apply to macro properties.

Apply these macro-specific rules:

- use `PascalCase` for macro classes
- use `camelCase` for public properties and slots
- use `snake_case` for private Python attributes and helper methods
- declare only operator inputs and concise results needed by the procedure
- set `AccessMode.READONLY` explicitly for macro-owned feedback
- do not specify `Assignment` without a concrete need; device instantiation
  assignment semantics are normally unnecessary for macros
- do not use mutable Python objects as function default arguments

Apply the middlelayer value, unit, and timestamp guidance unchanged.

## 6. Macro Slots, State, And Cancellation

Prefer `@MacroSlot(...)` for public macro actions. It starts either a
synchronous function or coroutine function in a background task and replies to
the initiating slot call immediately. Use ordinary `@Slot(...)` only when its
different completion and reply semantics are explicitly required.

Macro actions automatically use a passive/active state pair:

- an action is callable in the passive state
- starting it moves the macro to the active state
- completion restores the passive state
- the macro exposes cancellation for the current action

Do not manually create a broader device state machine. If custom states are
essential, use a middlelayer device.

Cancellation is cooperative and is delivered at framework synchronization
boundaries. Arbitrary blocking Python or native work cannot be interrupted
safely. Therefore:

- keep every operation bounded
- place safe cleanup and device stopping in `finally` or cancellation hooks
- do not assume cancellation reverses completed remote writes
- return remote devices to a safe condition when the procedure owns that
  responsibility

## 7. Remote Devices And Proxy Scope

Before using `getDevice`, `connectDevice`, `RemoteDevice`, proxy
properties, or proxy slots, read the middlelayer guide sections on remote
devices, proxy lifetime, remote operations, and waiting.

Apply these macro-specific rules:

- prefer a temporary `getDevice` context for one bounded procedure
- use `connectDevice` only when the connection must span several operations,
  and disconnect it promptly
- use `RemoteDevice` only for a static declared macro dependency whose
  managed monitoring behavior is genuinely needed
- keep every proxy referenced by a wait connected for the complete wait
- do not keep a proxy alive to implement permanent monitoring

A positive `RemoteDevice` timeout logs a missing dependency and lets startup
continue. A non-positive timeout may leave startup waiting indefinitely.

## 8. Remote Writes, Calls, And Locks

Read the middlelayer guide section on remote reads, writes, calls, and locks.
It owns the contracts for proxy assignment, `setWait`, `setNoWait`,
`execute`, `executeNoWait`, remote slot calls, acknowledgement, locking,
and remote failures.

Choose acknowledged operations whenever a later procedure step depends on
success. Use no-wait operations only when the macro deliberately does not
depend on acceptance, completion, or result.

## 9. Bounded Waiting And Monitoring

Read the middlelayer guide section on waiting and monitoring through proxies.
It owns the behavior of `waitUntil`, `waitWhile`, `waitUntilNew`, proxy
liveness, and event-driven updates.

Every wait must have a bounded timeout or another explicit termination
condition appropriate to the operation. Handle remote `ERROR`, disappearance,
and cancellation.

Do not leave an unbounded `while True` monitor in production macro code. A
macro may monitor one action for a bounded duration, but continuous monitoring
belongs in a middlelayer device. Persistent subscriptions can also create
substantial network traffic.

`@Monitor()` and `RemoteDevice(...)` may provide simple derived macro
properties. An update from any declared remote can recompute all monitor
properties; monitor failures are logged and monitoring continues. Keep these
computations inexpensive. If the monitor becomes control logic or an ongoing
service, migrate it to a device.

## 10. Pipeline Snapshots

Use `PipelineContext` only for a bounded snapshot from an output channel.
Use `get_image_data(...)` when a payload image or `NDArray` must be
extracted as a numpy array.

Validate the configured `<deviceId>:<channel>.<path>` shape, handle
`TimeoutError`, and release the pipeline context immediately after the
snapshot.

Use a middlelayer device for continuous pipeline consumption, forwarding,
distribution, or transformation. Read the middlelayer pipeline and image
sections when payload schema, metadata, image, or buffer semantics matter.

## 11. Topology Access

Read the middlelayer topology and discovery section before implementing
topology-dependent behavior.

Subclass `TopologyMacro` only when the procedure genuinely needs the full
Karabo topology. It enables `getTopology()`, whose groups include `device`,
`server`, `macro`, `client`, and `unknown`. Filter discovered elements
by topology attributes such as `classId`; do not generate device IDs from
assumptions when discovery is available.

Full topology subscription has startup and network cost. Use a normal `Macro`
for one or a few known devices.

## 12. History

Read the middlelayer history and persistent configurations section. It is the
single source of truth for `getHistory`,
`getConfigurationFromPast`, time handling, returned values, service
dependencies, and errors.

Keep history queries bounded and handle missing data, service errors, and
timeouts as normal operational outcomes.

## 13. iKarabo

iKarabo is an IPython-based interactive client, not a separate macro language.
Use it for concise interaction with already instantiated devices:

- inspect or change one property
- execute one device action
- perform a short set-value-then-command sequence
- start an existing scan or procedure

Prefer one-liners or a few simple statements. Use a proxy for repeated
interaction and a convenience helper for one quick action. Save recurring
logic as a macro and implement complex persistent logic as a middlelayer
device.

## 14. Development And Execution

Macros are edited in a Karabo project macro folder and executed on a macro
server.

- use the development or debug macro server while designing and testing
- stop the current macro instance before editing it
- save changes before rerunning
- use the regular macro server only after the procedure is ready
- avoid blocking unrelated macros on a shared server

## 15. Error Handling And Cleanup

- validate preconditions before issuing remote actions
- let meaningful Karabo errors remain visible; never use bare `except: pass`
- distinguish request acknowledgement from operation completion
- set bounded deadlines for locks, waits, pipeline reads, and remote calls
- use `try/finally` to release contexts and locks
- on cancellation or partial failure, stop or restore remote devices when the
  procedure requires it
- print concise operator progress; use framework logging where durable
  diagnostics are needed and supported

When several devices are changed, define the failure policy before coding:
all-or-nothing validation, best effort, compensating rollback, or explicit
operator recovery. A sequence of successful writes is not automatically a
transaction.

## 16. Testing

For macro test work, read `pytest-testing.md` completely in addition to both
macro and middlelayer references. Test the macro as a bounded behavior:

- property and schema validation
- passive/active transitions around actions
- synchronized remote calls and acknowledgement choices
- cancellation and cleanup
- timeout and remote-error handling
- topology filters or pipeline snapshots where used

Keep macro implementation tests consistent with the selected sync or async
style. A Karabo or pytest test harness may itself be asynchronous when required
to host devices or observe broker behavior; do not infer the macro style from
the harness alone.

Prefer protocol-level test doubles or Karabo testing contexts over real
hardware. Ensure every proxy, task, lock, and pipeline context is released at
test teardown.

## 17. Common Mistakes

- mixing synchronous and asynchronous macro syntax without following the
  selection rules
- copying asynchronous device examples without adapting them to macro
  lifecycle and `MacroSlot` behavior
- implementing continuous monitoring in a macro
- adding a custom multi-state device state machine
- talking directly to hardware instead of using a Karabo proxy
- using fire-and-forget when the next step depends on success
- keeping temporary proxies or pipeline contexts alive indefinitely
- writing long loops or complex branching in `execute`
- assuming cancellation interrupts arbitrary blocking Python or native code
- swallowing exceptions and reporting success after partial failure
- subclassing `TopologyMacro` for one known remote device
- using assignment metadata that has no useful macro semantics
- duplicating shared middlelayer API rules in this guide

## 18. Recommended Default Architecture

1. Read this guide and the relevant middlelayer guide sections.
2. Declare only operator inputs and concise result properties.
3. Expose one primary action with `@MacroSlot(...)`, using sync by default or
   async when requested or already established.
4. Acquire temporary proxies inside that action.
5. Use acknowledged writes and calls where later steps depend on success.
6. Wait event-first with explicit termination conditions and deadlines.
7. Handle cancellation and partial failure with deterministic cleanup.
8. Release proxies and pipeline contexts promptly.
