## How to work here

### Think before you code.

- State your assumptions. If you are not sure, ask.
- If the task can be read more than one way, say so. Do not pick silently.
- If a simpler approach exists, say so. Push back when it helps.

### Keep it simple.

- Write the least code that solves the task. Nothing speculative.
- No features that were not asked for. No "just in case" flexibility.
- No error handling for cases that cannot happen.
- If you wrote 200 lines and 50 would do, write the 50.

### Make surgical changes.

- Change what the task needs, and not more.
- Do not reformat or refactor code you were not asked to touch.
- Match the style around you, even if you would do it differently.
- If you spot unrelated dead code, mention it. Do not delete it.
- Clean up only the imports and names your own change left unused.
- Surgical means no gratuitous changes. It does not mean copy code to avoid
  touching a shared function. Reuse beats duplication (see Code we want).

### Work towards a clear goal.

- Turn the task into something you can check. "Add validation" becomes "write a
  test for the invalid input, then make it pass."
- For multi-step work, state a short plan first.
