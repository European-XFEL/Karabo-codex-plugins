---
name: karabo-cpp-coroutines
description: Draft guidance for developing new C++20 Boost Cobalt coroutine code and converting existing callback or synchronous workflows in Karabo C++ framework components and devices. Use for Karabo C++ coroutine APIs, AMQP, TCP, WebSocket, and coroutine lifecycle work. Contains branch-derived examples and explicit unresolved design questions; excludes Python async code and project-wide migration planning.
---

# Karabo C++ Coroutines

## Scope

Develop Karabo coroutine code using project decisions, upstream guidance, and
revision-specific Framework examples. The [guidance reference](references/open-decisions.md)
uses **PD** for project decisions and **UG** for upstream guidance. Code
observations identify their revision; remaining questions stay explicit.

Support both new coroutine code and conversion of an existing C++ workflow.
Keep rollout sequencing, device inventories, migration schedules, and
project-wide strategy outside this skill.

Read the target repository's instructions and Karabo AI policy before proposing
or making changes. For ordinary C++ device schema, slot, state, and lifecycle
context, consult the bundled
[C++ development guide](../karabo-device-development/references/AGENTS.cpp.md).
It describes the existing device API; it does not establish coroutine support
for slot registration or destruction.

## Choose the Relevant Material

- For AMQP operations, callback adapters, and broker messaging, read the AMQP
  section and newer revision notes in [branch material](references/branch-material.md).
- For TCP, WebSocket, framing, and channel APIs, read the transport section of
  [branch material](references/branch-material.md).
- Before choosing toolchains, coroutine types, execution, callback adapters,
  ownership, errors, or lifecycle behavior, read the relevant
  [guidance and remaining questions](references/open-decisions.md).
  C01–C10 separate usable guidance from unresolved project contracts.
- For device integration, read the lifecycle and slot sections there. Neither
  branch provides a complete reference device establishing those conventions.

## Use the Draft in a Concrete Task

1. Identify whether the request concerns new code or a conversion, and which
   operation and API boundary it covers. Inspect the target checkout's actual
   APIs and dependencies; branch APIs may not be present.
2. Use the pinned source map to find relevant examples when source inspection
   is authorized. Do not assume a similarly named method has identical behavior
   in another revision.
3. Record the operation's execution context, ownership across suspension,
   completion/error behavior, and shutdown path. Resolve these from existing
   target contracts or explicit task decisions, not from an unanswered question.
4. For a conversion, preserve observable ordering, replies, error reporting,
   framing, and queue behavior unless the task explicitly changes them. For new
   code, state these contracts before selecting an example to adapt.
5. Validate the affected behavior in the required development environment.
   Use C10 to select tests and address known harness gaps; branch tests are
   examples of scenarios, not evidence that the target implementation passes.

When maintaining this skill, inspect relevant Framework code and official
references to resolve questions when the task requests it. Keep implementation
changes outside documentation work. For a concrete implementation task, use an
established local contract where available and identify any remaining decision
that materially blocks the requested behavior.

## Maintain the Evidence

Use **PD** only for supplied project choices and **UG** for cited upstream
contracts or recommendations. Describe Framework behavior with the revision,
path, and symbol; do not turn a branch observation into a universal convention.
Keep inference explicit. Source inspection is not runtime validation.

Replace answered questions with scoped guidance and supporting references.
Keep only unresolved decisions and missing validation under **Open**. Maintain
one authoritative explanation and link to it rather than duplicating it.
