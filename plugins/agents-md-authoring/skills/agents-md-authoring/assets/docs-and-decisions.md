## Docs and decisions

- Write docs and comments in plain, direct English. Short sentences. Assume a
  tired reader. The exception is machine-facing files like schemas.
- A durable design decision goes in `docs/decisions/` as a short record. See
  the records already there for the shape. Always respect decisions already
  present there. If the current request is in conflict with a previously
  taken decision, ask how to proceed. DO NOT simply revise decisions on your
  own!
- Read `docs/decisions/` before you propose or add a new mechanism.
- Day-to-day reasoning goes in the merge request description, not a file in the
  repo. We do not keep a running log.
- Hit something undecided, a gap, or a "how do we proceed" question? Add a line
  to `docs/open-questions.md` under the right domain.
