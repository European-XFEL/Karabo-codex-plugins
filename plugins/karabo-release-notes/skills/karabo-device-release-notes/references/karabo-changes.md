# Interpreting Karabo changes

The Python package parses Python AST; it does not import or instantiate devices. It sees
local inheritance and many descriptor declarations, but cannot fully resolve
external bases, generated schemas, runtime injection or arbitrary expressions.
Inspect code when evidence is incomplete; do not turn uncertainty into a proven
breaking change or claim that static compatibility proves runtime compatibility.

An exposed property or slot is an interface used by scenes, macros, clients and
stored configurations. Removal, renaming, type changes, narrower allowed states,
restricted access or tighter configuration limits can affect those consumers.
A default-value change is worth describing with the old and new values. Preserve
exact case: `Slot`, `slot`, `Overwrite`, device names and member names are not
interchangeable. A member added to a base class should usually be described once
with its affected subclasses, except where overrides change the effective result.

Explain behavior independently of commit wording. "fix typo" can hide an interface
rename; "refactor" can change state transitions. Conversely, a log-level edit or
internal helper rename is not automatically a release note. Read the changed code
and its callers/tests when the observable consequence is unclear.

Use Added, Changed, Deprecated, Removed, Fixed and Security as appropriate to the
engine's categories. Preserve explicit breaking labels and migration instructions.
Describe only changes supported by the selected revision interval. CI configuration
and test-only mock devices can be false positives; investigate them rather than
silently erasing protected interface findings through a prose-only override.
