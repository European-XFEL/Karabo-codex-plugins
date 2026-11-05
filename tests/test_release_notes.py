"""Run with the release-notes engine installed: python -m unittest discover -s tests."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'plugins/karabo-release-notes/skills/karabo-device-release-notes/scripts/release_notes.py'
spec = importlib.util.spec_from_file_location('skill_bridge', HELPER)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class ReleaseNotesSkillTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.source = self.repo / 'device.py'
        self.source.write_text('from karabo.middlelayer import Device, Slot\nclass Motor(Device):\n    @Slot()\n    async def move(self): pass\n')
        (self.repo / 'mkdocs.yml').write_text('site_name: Motor\nnav:\n  - Home: index.md\n')
        (self.repo / 'changelog.md').write_text('# Draft only\n')
        self.commit()
        self.git('tag', '1.0.0')
        self.source.write_text(self.source.read_text().replace('pass', 'return 1'))
        self.commit()
        self.git('tag', '1.1.0')
        self.source.write_text('from karabo.middlelayer import Device\nclass Motor(Device): pass\n')
        self.commit()
        self.git('tag', '2.0.0')
        self.bundle = self.root / 'bundle'
        self.run_helper('prepare', '--repo', str(self.repo), '--all-tags', '--base', '1.1.0',
                        '--target', '2.0.0', '--output', str(self.bundle))
        self.proposal = self.root / 'proposal.json'
        self.proposal.write_text('{"intervals": []}')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Update device')

    def run_helper(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(HELPER), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr)
        return result.stdout

    def finish(self, *args, expected=0):
        return self.run_helper('finish', '--bundle', str(self.bundle / 'analysis.json'),
                               '--summaries', str(self.proposal), *args, expected=expected)

    def test_preview_is_bounded_and_read_only(self):
        before = self.git('show-ref')
        text = self.finish()
        self.assertIn('## [2.0.0]', text)
        self.assertIn('**Breaking:**', text)
        self.assertNotIn('## [1.1.0]', text)
        self.assertNotIn('Draft only', text)
        self.assertEqual(before, self.git('show-ref'))
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_write_updates_only_docs_on_new_branch(self):
        self.finish('--write', '--branch', 'release-notes/test')
        self.assertEqual(self.git('branch', '--show-current'), 'release-notes/test')
        self.assertTrue((self.repo / 'docs/CHANGELOG.md').exists())
        self.assertFalse((self.repo / 'CHANGELOG.md').exists())
        self.assertIn('Changelog:', (self.repo / 'mkdocs.yml').read_text())
        self.assertEqual((self.repo / 'changelog.md').read_text(), '# Draft only\n')
        self.assertEqual(self.git('diff', '--cached'), '')

    def test_cannot_remove_protected_finding(self):
        candidate = json.loads((self.bundle / 'candidates.json').read_text())[0]
        entry = candidate['entries'][0]
        self.proposal.write_text(json.dumps({'intervals': [{'target_sha': candidate['target_sha'],
            'summaries': [{'id': entry['id'], 'summary': '', 'include': False}], 'duplicates': []}]}))
        self.finish('--write', expected=2)
        self.assertEqual(self.git('branch', '--show-current'), 'main')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_tampered_findings_are_rejected(self):
        path = self.bundle / 'analysis.json'
        bundle = json.loads(path.read_text())
        bundle['report']['findings'] = []
        path.write_text(json.dumps(bundle))
        self.finish('--write', expected=2)
        self.assertEqual(self.git('branch', '--show-current'), 'main')

    def test_summary_is_applied_without_losing_breaking_label(self):
        candidate = json.loads((self.bundle / 'candidates.json').read_text())[0]
        entry = candidate['entries'][0]
        self.proposal.write_text(json.dumps({'intervals': [{'target_sha': candidate['target_sha'],
            'summaries': [{'id': entry['id'], 'summary': entry['summary'] + '; the command is no longer available',
                           'include': True}], 'duplicates': []}]}))
        preview = self.finish()
        self.assertIn('the command is no longer available', preview)
        self.assertIn('**Breaking:**', preview)

    def test_full_history_includes_initial_release(self):
        self.bundle = self.root / 'full-bundle'
        self.run_helper('prepare', '--repo', str(self.repo), '--all-tags',
                        '--target', '2.0.0', '--output', str(self.bundle))
        preview = self.finish()
        self.assertIn('## [1.0.0]', preview)
        self.assertIn('Initial tagged release.', preview)

    def test_unknown_id_rejected(self):
        candidate = json.loads((self.bundle / 'candidates.json').read_text())[0]
        self.proposal.write_text(json.dumps({'intervals': [{'target_sha': candidate['target_sha'],
            'summaries': [{'id': 'invented', 'summary': 'A change', 'include': True}], 'duplicates': []}]}))
        self.finish(expected=2)


if __name__ == '__main__':
    unittest.main()
