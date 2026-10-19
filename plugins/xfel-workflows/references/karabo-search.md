# Search request recipes

Use the shared `xfel_api.py` helper from [credentials.md](credentials.md).
Examples below use one collection; repeat inspection and search for both exact
collection names in the skill. Save intermediate JSON in a private task-local
temporary directory, not the repository.

## Inspect configuration and payload

```bash
python3 "$XFEL_API" qdrant GET '/collections/code_karabodevices3_project_summaries'
python3 "$XFEL_API" qdrant POST '/collections/code_karabodevices3_project_summaries/points/scroll' --data-file /private/path/sample.json
```

`sample.json`:

```json
{"limit": 2, "with_payload": true, "with_vector": false}
```

Look at `result.config.params.vectors` for size, distance, and named vectors,
and `payload_schema` for indexed fields. Actual payload samples are needed
because that schema does not describe every payload field. A sample alone does
not establish ingestion normalization, truncation, or quantization settings.
Where these differ from the model's normal float output, obtain ingestion
configuration before querying. Never modify collections, payloads, or indexes.

## Embed and query

Create an embedding request with a JSON serializer, using the technical query
as input. The model's retrieval prefix belongs on the query, exactly once:

```json
{
  "model": "mixedbread-ai/mxbai-embed-large-v1",
  "input": "Represent this sentence for searching relevant passages: Karabo device controlling a motor over Modbus with limit switches",
  "encoding_format": "float"
}
```

```bash
python3 "$XFEL_API" embedding POST '/embeddings' --data-file /private/path/embedding-request.json
```

Read `data[0].embedding` from the response. Check it is a finite numeric array
and its length matches the selected collection vector size. Serialize the
actual array into a Qdrant request body (the `query` below is illustrative):

```json
{"query": [0.1, 0.2, 0.3], "limit": 8, "with_payload": true, "with_vector": false}
```

For a named vector, add `"using": "the-observed-vector-name"`. Omit `using`
for an unnamed vector. Query each collection independently with its matching
configuration; do not assume their dimensions/names agree.

```bash
python3 "$XFEL_API" qdrant POST '/collections/code_karabodevices3_project_summaries/points/query' --data-file /private/path/query.json
```

Read hits from `result.points`. Keep point ID, score, collection name, and
payload provenance. If this instance lacks the query API, report the version
limitation rather than assuming a failed search means there are no devices.

## GitLab source

Resolve a full namespace path with percent-encoding (`/` becomes `%2F`) or use
the numeric project ID from verified metadata. All paths below are relative to
the configured GitLab base URL plus `/api/v4`:

| Purpose | GET path |
| --- | --- |
| Resolve project | `/projects/Karabo%2Fexample` |
| Resolve revision | `/projects/123/repository/commits/URL_ENCODED_REF` |
| Browse tree | `/projects/123/repository/tree?ref=COMMIT_SHA&per_page=100&page=1` |
| Browse subtree | `/projects/123/repository/tree?ref=COMMIT_SHA&path=URL_ENCODED_PATH&per_page=100&page=1` |
| Read file JSON | `/projects/123/repository/files/src%2Fdevice.py?ref=COMMIT_SHA` |

Decode the file response's `content` using its declared `encoding` (normally
base64) to inspect source. Prefer this JSON endpoint to `/raw`, which the helper
does not support as a JSON response. Page tree listings until exhausted or
explicitly state the subset examined. Read local project instructions before
using code for implementation. Cite `web_url/-/blob/COMMIT_SHA/path#L123` for
verified code locations, using the resolved project's actual `web_url`.

Official references: [collection configuration](https://qdrant.tech/documentation/manage-data/collections/),
[query API](https://api.qdrant.tech/api-reference/search/query-points),
[scroll API](https://api.qdrant.tech/api-reference/points/scroll-points),
[model query prefix](https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1),
[GitLab trees](https://docs.gitlab.com/api/repositories/), and
[file API](https://docs.gitlab.com/api/repository_files/).
