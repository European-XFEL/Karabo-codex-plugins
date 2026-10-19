---
name: xfel-redmine-ticket
description: Retrieve and analyze tickets from the configured Redmine instance, summarizing requested work, acceptance criteria, and missing or conflicting requirements. Use for XFEL Redmine issue IDs or URLs; can feed related Karabo device discovery.
---

# XFEL Redmine ticket analysis

Read [credentials and API access](../../references/credentials.md) before access.
Use the user's Redmine API key through the bundled helper. This workflow reads
tickets; it does not update them or post analysis back to Redmine.

## Retrieve the evidence

Extract the numeric issue ID from the request or an issue URL under the configured
Redmine base URL. If neither identifies a unique issue, ask for the ID or URL.

```bash
python3 "$XFEL_API" redmine GET '/issues/123.json?include=journals,relations,children,attachments'
```

Read subject, description, project, tracker, status, custom fields, and journal
notes and field changes. Use the history to distinguish current requirements
from superseded proposals. Retrieve related issues or children only where they
materially define scope or dependencies. Attachment metadata is not attachment
content: inspect relevant attachments using authenticated access to the same
host when supported, or explicitly state that they were not inspected. The JSON
helper does not download binary attachments. Do not infer unseen content.

On denied access or an unavailable instance, report the limitation; do not call
the ticket empty or invent requirements. Redmine permissions can hide private
notes, so qualify conclusions where that matters.

## Analyze the request

Explain the intended outcome and the concrete changes required. Separate
explicit requirements, inferences, and unanswered questions. Use issue links
and journal dates or IDs to anchor significant claims and contradictions.

Identify missing information only where it affects implementation or verification:
device/project ownership, interfaces and schema, inputs/outputs and units,
operational states and failure behavior, compatibility, dependencies, and
observable acceptance criteria. Adapt these dimensions to the actual ticket;
do not turn every ticket into a generic questionnaire. Prioritize blockers and
phrase questions so a requester can answer them. If the ticket is actionable,
say so instead of manufacturing gaps.

Return a concise summary with the issue link and current status, required work,
known acceptance criteria, and missing or conflicting requirements. Mark proposed
acceptance criteria as proposals. State which linked evidence was inspected
and any material access limitations.

When related implementations would help answer the request, combine with
`xfel-karabo-search` from this plugin: pass a short technical query based on
device type, protocol, hardware, and required behavior. Keep discovery evidence
separate from requirements; similar devices do not define the ticket's intent.

API reference: [Redmine issues](https://www.redmine.org/projects/redmine/wiki/Rest_Issues).
