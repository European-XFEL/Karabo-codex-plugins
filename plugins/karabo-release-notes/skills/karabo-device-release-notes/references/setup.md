# Local setup and GitLab CI

## Install dependencies

Requires Python 3.10+, Git with complete history/tags, and the separately installed
`karabo-release-notes` Python package. The helper is tested against package commit
`801e7ff0e7e3b3e8d4c8931d24d0af7cb95e042c`.

For development, use the package checkout's virtual environment, or:

```bash
python3 -m venv /tmp/release-notes-env
/tmp/release-notes-env/bin/pip install /path/to/karabo-release-notes
```

For reproducible installation after that commit is published and accessible:

```bash
python3 -m pip install 'git+ssh://git@git.xfel.eu:10022/Karabo/karabo-release-notes.git@801e7ff0e7e3b3e8d4c8931d24d0af7cb95e042c'
```

From this marketplace, install `karabo-release-notes@karabo`. Install
`karabo-device-development@karabo` for additional API guidance. Start a new Codex
session, then ask for `$karabo-device-release-notes` with the repository and release range.
Set `SKILL_DIR` to the installed skill directory, then run:

```bash
python "$SKILL_DIR/scripts/release_notes.py" prepare \
  --repo /path/to/device --base 3.4.4 --target 3.6.0 \
  --output /tmp/runmanagement-release-analysis
python "$SKILL_DIR/scripts/release_notes.py" finish \
  --bundle /tmp/runmanagement-release-analysis/analysis.json \
  --summaries /tmp/runmanagement-summaries.json --write
```

Use `--write --branch NAME` when a new branch is requested; omit `--write` for a preview.

## GitLab CI

Use the same `karabo-device-release-notes` skill in the Codex invocation. The
consuming CI project supplies the target revision and output behavior, and handles
its own Codex authentication and retention of changes. Use the same `prepare` and `finish` commands as above.
