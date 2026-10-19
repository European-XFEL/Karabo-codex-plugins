---
name: xfel-gitlab-mr
description: Prepare and create merge requests on the configured GitLab instance using the user's personal GitLab credentials. Use when asked to open an XFEL GitLab MR for a specific source branch and target project or branch.
---

# XFEL GitLab merge requests

Read [credentials and API access](../../references/credentials.md). Use the
user's personal GitLab token with the MR permissions documented there through the bundled helper.
Inspect and prepare locally before creation. A request to analyze a ticket or
find related code does not itself authorize creating an MR.

## Establish the proposed change

Determine the exact target project, source project (which may be a fork),
source branch, and target branch from the user's request and repository metadata.
Resolve project metadata with `GET /projects/:id`. Do not require `GET /user`
as a token validity test; fine-grained tokens may lack that unrelated permission.
Encode namespace paths as one URL component, or use numeric
project IDs. If the target branch was not supplied, use the project's declared
default branch when consistent with repository contribution instructions;
otherwise resolve the ambiguity with the user.

Inspect the relevant diff, commit history, working-tree state, contribution
instructions, and validation results. Report uncommitted changes that will not
appear in the MR. Check that the source branch exists remotely and contains
the intended commits. If pushing is needed and authorized by the request, use
the user's Git authentication; never embed a token in the remote URL. Do not
force-push, commit unrelated work, or create an empty MR. Ask about unresolved
project/branch ambiguity before any publication.

Prepare the exact title and description in files before the mutation. Lead with
the concrete problem and resulting behavior; include relevant validation and
known limitations. Preserve a project MR template when applicable. Link related
Redmine tickets as evidence without inventing closing-keyword behavior. Mark
an MR as draft only when requested or warranted by incomplete work, explaining why.

## Create once

Check for existing open MRs on the target project using
`GET /projects/:target_id/merge_requests?state=opened&source_branch=...&target_branch=...`;
URL-encode the branch values, paginate, and compare `source_project_id` as well.
If the exact MR already exists, return its link. Do not update it unless requested.

Immediately before creating the MR, confirm that user authorization covers
publication to the resolved project and branches. An explicit request to create
that MR supplies authorization; do not add a redundant approval step. If it is
not covered, present the completed title, description, and branch pair and ask
for permission before POST.

Serialize a JSON body with `source_branch`, `target_branch`, `title`, and
`description`. For a fork, POST to the **source** project's endpoint and set
`target_project_id` to the numeric target project ID. Omit optional settings
such as reviewers, labels, squash, and source-branch deletion unless requested
or required by the project's contribution instructions.

```bash
python3 "$XFEL_API" gitlab POST '/projects/123/merge_requests' --data-file /private/path/mr.json
```

Do not blindly retry a timed-out or failed POST. First check whether a matching
MR was created, including source project and both branches. Retry only after
establishing no matching MR exists and correcting a definite cause; otherwise
report the uncertain outcome for inspection. Do not merge, approve, or enable
automatic merge as part of creation.

Read the returned MR by project ID and IID to verify title, description, source
project/branch, and target project/branch. Return its web URL and summarize
validation actually performed; do not claim a running pipeline passed.

API reference: [GitLab merge requests](https://docs.gitlab.com/api/merge_requests/).
