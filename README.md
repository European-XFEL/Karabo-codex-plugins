# Karabo Codex Plugins

This repository is the shared source for Karabo plugins used by Codex CLI, developer workstations, and GitLab CI.

## Available plugins

- `karabo-device-development`: API-specific implementation, review, debugging,
  and testing guidance for C++, bound-Python, and middlelayer Karabo devices,
  including targeted pytest work, regression tests, failure diagnosis, and
  behavior-driven coverage improvement.

## Install from GitLab

Register this marketplace once:

```bash
codex plugin marketplace add \
  ssh://git@git.xfel.eu:10022/Karabo/codex-plugins.git \
  --ref main
```

Install the plugin:

```bash
codex plugin add karabo-device-development@karabo
```

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

## GitHub mirror

After a successful push pipeline on `main`, CI mirrors all GitLab branches and tags to
`European-XFEL/Karabo-codex-plugins` on GitHub. The mirror updates or deletes GitHub
branches and tags to match GitLab, so make changes in GitLab only.

Set `GITHUB_MIRROR_TOKEN` as a masked, protected GitLab CI/CD variable. Use a GitHub
token with read and write access to the destination repository's contents. If this
repository gains GitHub Actions workflows, the token also needs workflow write access.

## Repository layout

```text
.agents/plugins/marketplace.json
plugins/
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

1. Update the bundled skill and its references.
2. Increment the semantic version in `plugins/karabo-device-development/.codex-plugin/plugin.json`.
3. Run the repository validation pipeline.
4. Create a matching Git tag, for example `v0.2.0`.
5. Update consuming CI projects to the new tag after review.

## License

This repository is licensed under [Creative Commons Attribution 4.0 International](LICENSE).
