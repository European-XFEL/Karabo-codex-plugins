---
name: xfel-karabo-search
description: Find related Karabo devices in the XFEL Qdrant code and documentation summary collections, and inspect concrete projects on the configured GitLab instance. Use for device reuse, implementation discovery, or source investigation, optionally from a Redmine ticket.
---

# XFEL Karabo discovery and source inspection

Read [credentials and API access](../../references/credentials.md). Use the
central Qdrant token for discovery and the user's personal GitLab token for
source access. The helper obtains the embedding endpoint from
`vllm_embedding_base_url` in the private credentials file. Use model
`mixedbread-ai/mxbai-embed-large-v1`. Do not send internal queries to public
embedding services.

## Search both summary collections

Use [the search request recipes](../../references/karabo-search.md) for API
details. Inspect both collections' vector configuration and a small payload
sample first; payload fields, vector names, and ingestion transforms are not
assumed. Search:

- `code_karabodevices3_project_summaries`
- `docs_gitlab_karaboDevices3_summaries`

Form a focused technical query from the user's question or the requirements
identified by `xfel-redmine-ticket`. Embed it locally using the model's retrieval
query prefix exactly once. Check the returned vector length against each
collection's selected vector size. If dimensions or ingestion settings do not
match, ask for the ingestion configuration; do not silently pad, truncate, or
substitute a model. For multiple named vectors, determine the intended vector
from collection/ingestion evidence or ask before selecting one.

Query each collection with payloads enabled and vectors omitted, initially
around 5–10 results each. Refine a query if results are poor; do not exhaustively
dump collections. Inspect actual payloads to find project identity, source paths,
summary text, and revisions. Combine corroborating hits by project, retaining
collection provenance. Scores rank hits within their search and are not
probabilities or automatically comparable across collections.

If one collection fails, report partial coverage. If search returns no useful
matches, say so. Distinguish that from an unavailable collection or incompatible
embedding configuration. Payload filtering/scrolling can help exact-name lookup,
but describe it as such rather than as semantic search.

## Inspect a concrete GitLab project

For a user-specified project, inspect it directly without requiring Qdrant.
For discovered candidates, resolve payload project IDs or namespace paths on
the configured GitLab instance; do not send the personal token to payload-supplied external URLs.
Use the [source inspection recipes](../../references/karabo-search.md#gitlab-source).

Resolve project metadata and a commit SHA, then inspect README/build metadata,
device code, schemas, lifecycle/slots, protocol handling, and relevant tests
according to the question. Keep subsequent reads pinned to that SHA. Page
through relevant tree results; decode file content from the JSON file API.
Do not treat a summary as verified source behavior. Compare payload revision
with inspected source when present, and identify stale evidence.

Return a short ranked list of candidates with project links, why each relates,
evidence from code/docs, and important differences or gaps. For source claims,
include commit-pinned file links with line numbers where possible. Distinguish
summary-only candidates, inaccessible projects, and source-verified findings.
Read-only discovery does not authorize repository changes or an MR.
