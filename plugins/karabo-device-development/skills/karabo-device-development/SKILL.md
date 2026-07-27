---
name: karabo-device-development
description: Implement, review, debug, and test Karabo devices across the classic C++, bound-Python, and asynchronous middlelayer APIs. Use when a task involves karabo::core::Device, PythonDevice, karabo.bound, karabind, karabo.middlelayer, Karabo device schemas, slots, channels, proxies, DeviceClient, lifecycle behavior, or device tests.
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
- Route explicit middlelayer, middle layer, MDL, or Karabo asynchronous Python
  device requests to `references/AGENTS.middlelayer.md`.
- Route code importing `karabo.middlelayer`, subclassing its `Device`,
  `DeviceClientBase`, or `Macro`, or combining descriptor class attributes
  with `@Slot`, `@slot`, `InputChannel`, `OutputChannel`, `onInitialization`,
  `getDevice`, `connectDevice`, `setWait`, or `background` to
  `references/AGENTS.middlelayer.md`.

Do not route from generic symbols such as `Hash`, `State`, `String`, `Slot`,
`Configurable`, or `async def` alone. Require an API-specific import, base
class, or combination of characteristic symbols. Use the directory only as a
fallback.

Do not mix API implementation styles. If a task explicitly compares or
migrates APIs, keep each side internally consistent.

## Load The Guidance

Inspect the selected reference's table of contents before acting. Read the
sections relevant to the task, including the API's core mental model and common
mistakes. Read the complete selected reference for a new device, broad
architecture change, or cross-cutting review. Read more than one API reference
only for an explicit comparison, interoperability task, or migration.

Use heading searches to navigate the references:

```text
rg -n '^## ' references/AGENTS.cpp.md
rg -n '^## ' references/AGENTS.python-bound.md
rg -n '^## ' references/AGENTS.middlelayer.md
```

## Apply The Guidance

1. Inspect the target source, nearby devices, tests, and build metadata.
2. Follow the selected guide's schema, lifecycle, concurrency, communication,
   testing, and validation rules.
3. Reuse established repository patterns appropriate to the selected API.
4. Keep changes scoped to the requested behavior and preserve unrelated work.
5. Validate in proportion to risk with the commands and test layers identified
   by the selected guide.

When repository-local `AGENTS.md` instructions are present, follow them in
addition to this skill. Treat the repository instructions as authoritative if
they are more specific or newer.
