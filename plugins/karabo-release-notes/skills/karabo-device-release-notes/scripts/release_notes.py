"""Bridge Codex summaries to the independently installed release-notes engine."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import os
import tempfile


def intervals(report):
    if report.get('mode') == 'all-tags':
        return [r['analysis'] for r in report['releases'] if r['analysis']]
    return [report]


def candidates(report):
    result = deepcopy(report['entries'])
    for item in report['review']:
        result.append({'id': 'commit-' + item['commit'], 'summary': item['summary'],
                       'category': 'Changed', 'compatibility': 'potential',
                       'evidence': [item['commit']], 'finding_ids': [],
                       'affected_classes': [], 'migrations': [], 'kind': 'review'})
    return result


def apply_summaries(report, proposal):
    from karabo_release_notes.reconcile import apply_decisions, protected, facts
    if not isinstance(proposal, dict) or set(proposal) != {'intervals'}:
        raise ValueError('Expected an object with intervals')
    if not isinstance(proposal['intervals'], list):
        raise ValueError('intervals must be a list')
    result = deepcopy(report)
    by_sha = {r['target_sha']: r for r in intervals(result)}
    seen = set()
    for interval in proposal['intervals']:
        if not isinstance(interval, dict) or set(interval) != {'target_sha', 'summaries', 'duplicates'}:
            raise ValueError('Each interval needs target_sha, summaries, duplicates')
        sha = interval['target_sha']
        if sha not in by_sha or sha in seen:
            raise ValueError('Unknown or repeated interval')
        seen.add(sha)
        current = by_sha[sha]
        available = {e['id']: e for e in candidates(current)}
        retained = {e['id']: e for e in current['entries']}
        changed = set()
        if not isinstance(interval['summaries'], list):
            raise ValueError('summaries must be a list')
        for edit in interval['summaries']:
            if not isinstance(edit, dict) or set(edit) != {'id', 'summary', 'include'}:
                raise ValueError('Summary requires id, summary, include')
            identifier = edit['id']
            if identifier not in available or identifier in changed:
                raise ValueError('Unknown or repeated entry')
            changed.add(identifier)
            entry = available[identifier]
            text = edit['summary']
            if type(edit['include']) is not bool or not isinstance(text, str):
                raise ValueError('Invalid summary types')
            if not edit['include']:
                if protected(entry):
                    raise ValueError('Cannot discard structural, breaking or migration entries')
                retained.pop(identifier, None)
                continue
            if not text.strip() or any(c in text for c in '\n\r<>') or text.count('`') % 2:
                raise ValueError('Summary must be one Markdown line without HTML')
            if protected(entry) and not facts(entry['summary']) <= facts(text):
                raise ValueError('Structural summary must preserve explicit identifiers and numbers')
            entry['codex_summary'] = text.strip()
            entry['summary_source'] = 'codex-skill'
            retained[identifier] = entry
        current['entries'] = apply_decisions(list(retained.values()), {'duplicates': interval['duplicates']})
        current['summary_reconciliation'] = interval['duplicates']
        if changed or interval['duplicates']:
            current['recommendation_provisional'] = True
    return result



def write_current(repo, report):
    """Write generated docs on the checked-out branch without committing."""
    from karabo_release_notes.documentation import plan_changelog
    from karabo_release_notes.git import NotesError
    repo.require_clean()
    if repo.resolve('HEAD') != report['target_sha']:
        raise NotesError('Checked-out HEAD changed since analysis; prepare again for the current branch.')
    outputs = plan_changelog(repo, report)
    changed = {}
    target_files = set(repo.files(report['target_sha']))
    for name, content in outputs.items():
        old = repo.read(report['target_sha'], name) if name in target_files else None
        if old == content:
            continue
        path = repo.path / name
        if path.is_symlink():
            raise NotesError(f'Refusing to overwrite symlink {name}.')
        tracked = repo.git('ls-files', '--error-unmatch', '--', name, check=False).returncode == 0
        if path.exists() and not tracked:
            raise NotesError(f'Refusing to overwrite untracked or ignored {name}.')
        for parent in path.parents:
            if parent == repo.path:
                break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise NotesError(f'Unsafe documentation directory {parent.relative_to(repo.path)}.')
        changed[name] = content
    if not changed:
        return False
    created = []
    backups = {name: (repo.path / name).read_bytes() if (repo.path / name).exists() else None
               for name in changed}
    temporary = []
    try:
        for name, content in changed.items():
            dest = repo.path / name
            missing = []
            parent = dest.parent
            while parent != repo.path and not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir()
                created.append(directory)
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=dest.parent,
                                             prefix='.release-notes-', delete=False) as stream:
                stream.write(content)
                temporary.append(Path(stream.name))
            os.replace(temporary[-1], dest)
    except OSError:
        for name, data in backups.items():
            dest = repo.path / name
            if data is None:
                dest.unlink(missing_ok=True)
            else:
                dest.write_bytes(data)
        for temp in temporary:
            temp.unlink(missing_ok=True)
        for directory in reversed(created):
            directory.rmdir()
        raise
    return True

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--repo', required=True)
    prepare.add_argument('--base', default='auto')
    prepare.add_argument('--target', default='HEAD')
    prepare.add_argument('--all-tags', action='store_true')
    prepare.add_argument('--output', required=True, type=Path)
    finish = commands.add_parser('finish')
    finish.add_argument('--bundle', required=True, type=Path)
    finish.add_argument('--summaries', required=True, type=Path)
    finish.add_argument('--write', action='store_true', help='Write changelog changes locally')
    finish.add_argument('--branch')
    args = parser.parse_args(argv)
    # Keep --help usable without the separately installed engine.
    from karabo_release_notes.git import Repository, NotesError
    from karabo_release_notes.analysis import analyze
    from karabo_release_notes.history import analyze_history, update_history
    from karabo_release_notes.render import render
    from karabo_release_notes.cli import write_branch
    try:
        if args.command == 'prepare':
            repo = Repository(args.repo)
            report = (analyze_history(repo, args.target, args.base) if args.all_tags
                      else analyze(repo, args.base, args.target))
            if args.all_tags:
                report['bounded_history'] = args.base != 'auto'
            # Artifact writes are explicit; never silently replace an earlier analysis.
            args.output.mkdir(parents=True, exist_ok=False)
            bundle = {'repo': str(repo.path.resolve()), 'report': report}
            (args.output / 'analysis.json').write_text(json.dumps(bundle, indent=2) + '\n')
            compact = [{'target_sha': r['target_sha'], 'base_sha': r['base_sha'],
                        'base_ref': r['base_ref'], 'target_ref': r['target_ref'],
                        'entries': candidates(r)} for r in intervals(report)]
            (args.output / 'candidates.json').write_text(json.dumps(compact, indent=2) + '\n')
            print(args.output / 'candidates.json')
        else:
            bundle = json.loads(args.bundle.read_text())
            original = bundle['report']
            if original.get('schema_version') != 1:
                raise ValueError('Unsupported report version')
            repo = Repository(bundle['repo'])
            # Recompute from immutable commits: the editable bundle cannot alter findings.
            fresh = (analyze_history(repo, original['target_sha'], original['base_ref'])
                     if original.get('mode') == 'all-tags' and original.get('bounded_history')
                     else analyze_history(repo, original['target_sha'])
                     if original.get('mode') == 'all-tags'
                     else analyze(repo, original['base_sha'], original['target_sha']))
            if fresh['findings'] != original['findings']:
                raise ValueError('Analysis changed; prepare a fresh bundle')
            report = apply_summaries(fresh, json.loads(args.summaries.read_text()))
            if args.write:
                if args.branch:
                    branch = write_branch(repo, report, args.branch, False)
                    print('Created ' + branch if branch else 'No changelog changes')
                else:
                    changed = write_current(repo, report)
                    print('Updated changelog on ' + repo.git('branch', '--show-current').strip()
                          if changed else 'No changelog changes')
            else:
                print(update_history('', report) if report.get('mode') == 'all-tags'
                      else '## [Unreleased]\n\n' + render(report), end='')
    except (NotesError, OSError, ValueError, KeyError, TypeError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except ModuleNotFoundError as exc:
        print(f'error: missing dependency {exc.name}; install the release-notes engine in this Python environment (see references/setup.md)', file=sys.stderr)
        sys.exit(2)
