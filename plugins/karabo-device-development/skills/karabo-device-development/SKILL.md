---
name: karabo-device-development
description: Implement, review, debug, and test Karabo devices and macros across the classic C++, bound-Python, asynchronous middlelayer device, and synchronous or asynchronous macro APIs. Use when a task involves karabo::core::Device, PythonDevice, karabo.bound, karabind, karabo.middlelayer, Macro, MacroSlot, TopologyMacro, iKarabo, Karabo device schemas, slots, channels, proxies, DeviceClient, lifecycle behavior, or Python test work such as writing or extending pytest tests, adding regression tests during feature or bug-fix work, diagnosing test failures, designing fixtures, or improving coverage.
---

# Karabo Device Development

## Route The API

Determine the device API from both the request and the code being edited.

- Route explicit C++ device or classic C++ framework requests to
  `references/AGENTS.cpp.md`.
- Route code using `karabo::core::Device`, `expectedParameters(Schema&)`,
  `KARABO_REGISTER_FOR_CONFIGURATION`, `KARABO_SLOT`, `KARABO_ON_DATA`,
  `karabo::data::Hash`, or `karabo::core::DeviceClient` to
  `references/AGENTS.cpp.md`.
- Route explicit bound-Python, bound device, `pybind11`, or `karabind`
  requests to `references/AGENTS.python-bound.md`.
- Route code using `karabo.bound`, `karabind`, `PythonDevice`,
  `@KARABO_CLASSINFO`, `@KARABO_CONFIGURATION_BASE_CLASS`,
  `registerInitialFunction`, or bound `DeviceClient` to
  `references/AGENTS.python-bound.md`.
- Route explicit Karabo macro, HowToMacro, macro server, or iKarabo requests to
  both `references/AGENTS.macro.md` and `references/AGENTS.middlelayer.md`.
- Route code subclassing `Macro` or `TopologyMacro`, or using `MacroSlot`,
  `RemoteDevice`, or `Monitor` in a macro to both
  `references/AGENTS.macro.md` and `references/AGENTS.middlelayer.md`.
- Route explicit middlelayer, middle layer, MDL, or Karabo asynchronous Python
  device requests to `references/AGENTS.middlelayer.md`.
- Route code importing `karabo.middlelayer`, subclassing its `Device` or
  `DeviceClientBase`, or combining descriptor class attributes
  with `@Slot`, `@slot`, `InputChannel`, `OutputChannel`, `onInitialization`,
  `getDevice`, `connectDevice`, `setWait`, or `background` to
  `references/AGENTS.middlelayer.md`.

Do not route from generic symbols such as `Hash`, `State`, `String`, `Slot`,
`Configurable`, or `async def` alone. Require an API-specific import, base
class, or combination of characteristic symbols. Use the directory only as a
fallback.

Do not mix API implementation styles. If a task explicitly compares or
migrates APIs, keep each side internally consistent.

## Choose Macro Syntax

For code subclassing `Macro` or `TopologyMacro`, choose the authoring style
in this order:

1. Use asynchronous syntax when the user explicitly requests it.
2. Match asynchronous syntax already present in the macro being extended.
3. Otherwise default to synchronous syntax for accessibility users who may not know Python `async`/`await`.

In synchronous macro code, use `def`, call synchronized Karabo helpers such
as `connectDevice(...)`, `setWait(...)`, remote slots, and
`waitUntil(...)` directly, and use normal `with` contexts. In asynchronous
macro code, use `async def`, await those operations, including
`await connectDevice(...)` and `await waitUntil(...)`, and use `async with`
where required.

Do not convert existing asynchronous macro code to synchronous syntax merely
because sync is the default. Keep each changed macro internally consistent.

After completing a synchronous macro implementation, ask once whether the user
wants it converted to asynchronous syntax. If the user accepts, update the
given codebase to the async form. If the user declines, or has already
declined, do not ask again. Do not repeat an unanswered offer in the same task
or conversation.

Apply this choice only to macros. Do not change the asynchronous middlelayer
device model or its guidance when applying this macro policy.

## Route Python Test Work

Whenever the work creates, modifies, reviews, or diagnoses Python tests, read
`references/pytest-testing.md` in addition to the selected API reference. Do
this when the user requests tests directly and when tests are a normal part of
implementing a feature or bug fix.

Run coverage analysis only when the user asks to improve coverage, coverage is
needed to locate the requested untested behavior, or no concrete test target
was provided and coverage would materially help select one. Do not expand a
focused test request into unrelated coverage work.

Do not use the pytest reference for ordinary C++ unit tests unless the target
repository actually drives them through pytest.

## Load The Guidance

Inspect the selected reference's table of contents before acting. Read the
sections relevant to the task, including the API's core mental model and common
mistakes. Read the complete selected reference for a new device, broad
architecture change, or cross-cutting review. Except for the macro rule below,
read more than one API reference only for an explicit comparison,
interoperability task, or migration.

For every macro task, read both `references/AGENTS.macro.md` and
`references/AGENTS.middlelayer.md` completely. The macro may use any shared
middlelayer feature, including descriptors, values, proxies, remote calls,
locks, waits, topology, pipelines, and history. Treat the macro guide as the
policy and macro execution overlay. Apply its sync-or-async selection rules
before adapting shared middlelayer operations to macro code.

Use heading searches to navigate the references:

```text
rg -n '^## ' references/AGENTS.cpp.md
rg -n '^## ' references/AGENTS.python-bound.md
rg -n '^## ' references/AGENTS.middlelayer.md
rg -n '^## ' references/AGENTS.macro.md
```

For Python test work, read `references/pytest-testing.md` completely. Load it
alongside the relevant API reference so the shared test workflow and the
API-specific lifecycle rules both apply.

## Apply The Guidance

1. Inspect the target source, nearby devices, tests, and build metadata.
2. Follow the selected guide's schema, lifecycle, concurrency, communication,
   testing, and validation rules.
3. Reuse established repository patterns appropriate to the selected API.
4. Keep changes scoped to the requested behavior and preserve unrelated work.
5. Validate in proportion to risk with the commands and test layers identified
   by the selected guide.

For Python test work, route the user's intent before editing: implement the
requested behavior test, add a regression test with a feature or fix, diagnose
a failing test, or use coverage to discover valuable missing behavior. Treat
coverage as evidence, never as the assertion contract.

When repository-local `AGENTS.md` instructions are present, follow them in
addition to this skill. Treat the repository instructions as authoritative if
they are more specific or newer.
