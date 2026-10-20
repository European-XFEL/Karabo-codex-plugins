---
name: agents-md-authoring
description: >-
  Create or update concise, evidence-backed AGENTS.md files for Karabo
  repositories. Use when asked to inspect a Karabo device repository
  and write repository instructions for future coding agents. Do not use for
  audits, general documentation, or non-Karabo repositories.
---

# AGENTS.md Authoring

## Require Karabo Guidance

Use `$karabo-device-development` for every task handled by this skill. Let that
skill detect the API and load its own references; do not duplicate or explain
its routing logic here.

If `$karabo-device-development` is unavailable, stop and ask the user to
install the `karabo-device-development` plugin from the internal marketplace.
Do not substitute generic Karabo knowledge.

## Deliverable

Inspect the target repository, then create or update its root `AGENTS.md`
directly. Keep every line at no more than 79 characters. Create nested
`AGENTS.md` files only when a subtree has substantial, stable instructions
that differ from the root.

Do not produce an audit, evidence table, analysis report, proposed draft, or
documentation backlog. After editing, respond only with the paths created or
updated and a brief description of their scope.

## Establish Repository Evidence

Base instructions on current committed source code, tests, build metadata,
CI, and repository documentation. Inspect enough of these sources to identify:

- the project's purpose, architecture, and ownership boundaries;
- exact development, build, test, lint, and validation commands;
- test locations, fixtures, simulators, and external test requirements;
- lifecycle, communication, schema, state, concurrency, and persistence
  behavior that affects safe changes;
- compatibility-sensitive interfaces and external protocol mappings;
- generated files that must not be edited directly;
- operations that communicate with or change real hardware;
- expected dependencies and integrations with other Karabo projects; and
- an implemented `interfaces` property or another declared Karabo interface.

Use repository history only when current files do not establish why an active
constraint exists. Do not include temporary environment observations, missing
local tools, current failures, uncommitted experiments, or machine-specific
information.

## Select High-Value Instructions

Include only stable information that materially changes how future agents
should modify, test, or operate the repository.

- Do not invent commands, dependencies, conventions, or team policies.
- Do not add preferred designs or generic best practices the repository does
  not follow.
- Do not turn a possible bug, TODO, inconsistency, or improvement into a rule.
- Use `preserve`, `must`, `never`, and `do NOT` only when repository evidence
  or an explicit requirement in this skill establishes the constraint.
- Preserve distinctions the implementation intentionally gives different
  meanings; do not simplify them into one rule.
- Scope simulator and hardware restrictions to the operations they govern,
  not unrelated unit tests.
- Do not record language, runtime, compiler, Karabo, or operating-system
  versions.
- Do not repeat generic C++, bound-Python, middlelayer, macro, or pytest
  guidance already provided by `$karabo-device-development`.
- Record a consistent, repository-established deviation from that skill
  explicitly and narrowly.
- Do not copy implementation constants unless they define a critical external
  protocol contract.
- Describe a directory or file only when it helps locate the right
  implementation, test, generated output, or operational boundary.

Prefer a small number of actionable instructions over exhaustive coverage.

## Compose The Root File

Write in simple, plain English so each instruction is clear on the first
read. Use short sentences with concrete actions, and name the relevant
file or component when needed. Avoid jargon, unexplained shorthand, and
packing several rules into one sentence. Keep the file concise by removing
repetition and low-value detail, rather than compressing explanations until
they become unclear. Include enough context to preserve the intended meaning.

Start with one short paragraph explaining the project's purpose. Immediately
after that paragraph, copy `assets/root-working-agreements.md` verbatim. This
fragment is mandatory internal guidance and is not removed as generic during
the evidence review.

After the mandatory fragment, organize the repository-specific instructions
under only the headings the evidence warrants. Ensure the root file also:

- says `$karabo-device-development` must be available to agents working on the
  repository and directs them to request installation when it is absent;
- tells agents to prefer the existing Karabo installation referenced by
  `$KARABO` for development and testing;
- names repository-established dependencies and Karabo integrations and says
  they may not be changed without asking the user;
- tells agents not to mock a missing expected dependency, but to ask the user
  to install it in the Karabo environment referenced by `$KARABO`;
- identifies any implemented Karabo `interfaces` property and tells agents to
  check for a dedicated skill for that interface before changing it; and
- states precisely which operations can reach or alter real hardware.

Do not add a mandatory statement when the repository does not implement the
corresponding dependency, interface, protocol, or hardware behavior.

For a complex repository, read `assets/docs-and-decisions.md`. Include that
fragment only when the repository establishes the referenced documentation,
decision-record, and open-question paths. Otherwise omit it rather than
inventing a documentation process or nonexistent paths.

## Decide On Nested Files

Create a nested `AGENTS.md` only when a subtree has stable commands, safety
constraints, generated-code rules, ownership, or architecture that genuinely
differs from the root.

- Do not create one merely because a directory is large.
- Do not repeat root instructions.
- Keep repository-wide safety and compatibility rules in the root file.
- Add only subtree-specific instructions.

## Validate The Result

1. Check that every Markdown line is at most 79 characters and that the
   Markdown structure is valid.
2. Re-read every non-mandatory instruction and remove anything unsupported,
   generic, aspirational, temporary, duplicated, or overly detailed.
3. Check every mandatory repository-specific statement against the evidence.
4. Rewrite any sentence that requires rereading to understand what to do,
   when the rule applies, or which component it concerns.
5. Review the diff and do not change unrelated files.
6. Return only the changed paths and a brief scope description.
