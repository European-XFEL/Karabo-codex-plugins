# Karabo Codex Plugins

This repository is the shared source for Karabo plugins used by Codex CLI, developer workstations, and GitLab CI.

## Available plugins

- `karabo-device-development`: API-specific implementation, review, debugging,
  and testing guidance for C++, bound-Python, and middlelayer Karabo devices,
  including targeted pytest work, regression tests, failure diagnosis, and
  behavior-driven coverage improvement.

- `agents-md-authoring`: repository inspection and evidence-backed creation of
  concise `AGENTS.md` instructions for Karabo projects. Requires the
  `karabo-device-development` plugin.

## Install from GitLab

Register this marketplace once:

```bash
codex plugin marketplace add \
  ssh://git@git.xfel.eu:10022/Karabo/codex-plugins.git \
  --ref main
```

Use `main` for the latest unreleased content, or replace it with a repository
release tag to stay on a stable marketplace snapshot. Install either or both
plugins:

```bash
codex plugin add karabo-device-development@karabo
codex plugin add agents-md-authoring@karabo
```

The `agents-md-authoring` workflow requires `karabo-device-development`, so
install both when using it.

Start a new Codex session after installation so the bundled skill is loaded.

## Use in GitLab CI

For a private repository on the same GitLab instance, allow the consuming CI job token to read this project. Then run:

```yaml
variables:
  KARABO_CODEX_PLUGINS_REF: "0.1.2"

before_script:
  - >
    codex plugin marketplace add
    "https://gitlab-ci-token:${CI_JOB_TOKEN}@git.xfel.eu/Karabo/codex-plugins.git"
    --ref "${KARABO_CODEX_PLUGINS_REF}"
    --json
  - codex plugin add karabo-device-development@karabo --json
```

Prefer a release tag or commit instead of `main` in CI so agent behavior is reproducible.

A pinned consumer remains on that snapshot until its
`KARABO_CODEX_PLUGINS_REF` is changed. To receive newer marketplace content,
update the variable to a newer repository tag.

## Repository layout

```text
.agents/plugins/marketplace.json
plugins/
├── agents-md-authoring/
│   ├── .codex-plugin/plugin.json
│   └── skills/agents-md-authoring/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       └── assets/
└── karabo-device-development/
    ├── .codex-plugin/plugin.json
    └── skills/karabo-device-development/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── references/
        └── scripts/
            ├── analyze_coverage.py
            └── compare_coverage.py
```

## Releasing updates

This repository has two independent version layers:

- A repository Git tag identifies one complete marketplace snapshot. Increment
  the repository tag for every published repository update, regardless of how
  many plugins changed. Consumers can remain pinned to an older tag or update
  their configured `--ref` when they want the newer snapshot.
- Each plugin manifest has its own semantic `version`. Increment that version
  only when that particular plugin changes. Plugins that did not change keep
  their existing versions, even when the repository receives a new tag.

The repository tag and individual plugin versions are not required to match.
For example, repository tag `0.1.3` can contain
`karabo-device-development` version `0.1.2` and `agents-md-authoring` version
`0.1.0`. If only `agents-md-authoring` changes in the next release, increment
its plugin version to `0.1.1`, leave `karabo-device-development` at `0.1.2`,
and create the next repository tag for the complete updated snapshot.

Use semantic versioning for plugin manifests:

- Patch (`0.1.0` to `0.1.1`) for compatible fixes and guidance improvements.
- Minor (`0.1.0` to `0.2.0`) for new backward-compatible capabilities.
- Major (`0.1.0` to `1.0.0`) for incompatible behavior or interface changes.

1. Update any plugins, marketplace metadata, or repository documentation.
2. Increment the manifest version of every plugin that changed; do not change
   versions of unaffected plugins.
3. Run the repository validation pipeline.
4. After the change is merged, increment and create the next repository tag.
5. Consumers update their configured `--ref` only when they want that release.
