# Summary proposal

`prepare` writes `analysis.json` (analysis report and repository location) and
`candidates.json` (release intervals and candidate entries without diagnostics).
Keep the analysis bundle unchanged. Candidate evidence contains commit SHAs and/or
source locations that can guide targeted Git reads.

`finish` accepts this JSON object:

```json
{
  "intervals": [
    {
      "target_sha": "EXACT_SHA_FROM_CANDIDATES",
      "summaries": [
        {"id": "EXACT_ENTRY_ID", "summary": "Describe the supported behavior.", "include": true}
      ],
      "duplicates": []
    }
  ]
}
```

Omitted intervals and entries retain deterministic wording. Unclassified review
candidates are omitted unless explicitly included. A review candidate receives the
Changed category and provisional compatibility; this interface cannot invent new
structural findings or revise category/compatibility policy.

An included summary is one Markdown line without HTML; use balanced backticks for
identifiers. Structural summaries must retain all explicit identifiers and numbers
from the original summary. Leaving their summary untouched is often preferable.
Nonstructural, nonbreaking entries without migration notes can be excluded using
`include: false` and an empty summary when they are not noteworthy.

To remove a duplicate while retaining its evidence, use:

```json
{"remove": "REDUNDANT_ENTRY_ID", "covered_by": ["RETAINED_ENTRY_ID"]}
```

Put that object in `duplicates`. Several retained entries can collectively cover
one redundant entry. Every detail must be covered; identifiers and numbers are
checked mechanically, but Codex must also check conditions and meaning. Protected
entries cannot be removed. Keepers cannot also be removed in the same proposal.
Raw findings are preserved; absorbed IDs and evidence are attached to keepers.

`finish` recomputes the analysis from the recorded revisions, compares raw findings,
and validates the proposal before writing. Use bundles from your own local workflow.
