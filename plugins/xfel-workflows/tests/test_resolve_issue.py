"""Resolve board links to an exact issue without trusting unrelated IDs."""

import base64
import importlib.util
import json
from pathlib import Path
import unittest
from urllib.parse import urlencode


spec = importlib.util.spec_from_file_location(
    "resolve_issue", Path(__file__).parents[1]
    / "skills/xfel-gitlab-issue/scripts/resolve_issue.py"
)
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)
GITLAB_BASE = "https://gitlab.example.invalid"
PROJECT = "group/integration-requests"
BOARD = f"https://gitlab.example.invalid/{PROJECT}/-/boards"
EXAMPLE_SELECTION = base64.urlsafe_b64encode(json.dumps({
    "iid": "283", "full_path": PROJECT, "id": 15335
}).encode()).decode().rstrip("=")


def resolve(url):
    return resolver.resolve_issue(url, GITLAB_BASE)


def board_url(selection):
    encoded = base64.urlsafe_b64encode(json.dumps(selection).encode()).decode().rstrip("=")
    return BOARD + "?" + urlencode({"show": encoded})


class ResolverTests(unittest.TestCase):
    def test_supplied_board_selection_uses_iid_not_opaque_id(self):
        issue = resolve(BOARD + "?show=" + EXAMPLE_SELECTION + "#/")
        self.assertEqual(issue, {
            "project_path": PROJECT,
            "iid": 283,
            "api_path": "/projects/group%2Fintegration-requests/issues/283",
            "web_url": f"https://gitlab.example.invalid/{PROJECT}/-/issues/283",
        })

    def test_direct_issue_link_and_nested_namespace(self):
        issue = resolve("https://gitlab.example.invalid/group/subgroup/device/-/issues/42#note_17")
        self.assertEqual(issue["project_path"], "group/subgroup/device")
        self.assertEqual(issue["iid"], 42)
        self.assertEqual(issue["api_path"], "/projects/group%2Fsubgroup%2Fdevice/issues/42")

    def test_unpadded_selection(self):
        issue = resolve(board_url({"iid": 9, "full_path": PROJECT, "id": 888}))
        self.assertEqual(issue["iid"], 9)

    def test_work_item_link_uses_issue_rest_endpoint(self):
        issue = resolve(f"https://gitlab.example.invalid/{PROJECT}/-/work_items/283")
        self.assertEqual(issue["api_path"], "/projects/group%2Fintegration-requests/issues/283")

    def test_configured_origin_port_and_base_path(self):
        base = "https://custom.example.invalid:9443/gitlab"
        issue = resolver.resolve_issue(base + "/group/project/-/issues/7", base)
        self.assertEqual(issue["web_url"], base + "/group/project/-/issues/7")
        self.assertEqual(issue["api_path"], "/projects/group%2Fproject/issues/7")
        for url in (base.replace(':9443', '') + "/group/project/-/issues/7",
                    "https://custom.example.invalid:9443/other/group/project/-/issues/7"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                resolver.resolve_issue(url, base)

    def test_ambiguous_or_invalid_selection_rejected(self):
        for url in (
            BOARD,
            BOARD + "?show=not-base64",
            BOARD + "?show=" + EXAMPLE_SELECTION + "&show=" + EXAMPLE_SELECTION,
            board_url({"iid": 283, "full_path": "other/project"}),
            board_url({"id": 15335, "full_path": PROJECT}),
            board_url({"iid": "-1", "full_path": PROJECT}),
            board_url([283, PROJECT]),
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                resolve(url)

    def test_external_hosts_credentials_and_invalid_paths_rejected(self):
        for url in (
            f"http://gitlab.example.invalid/{PROJECT}/-/issues/283",
            f"https://other.example/{PROJECT}/-/issues/283",
            f"https://gitlab.example.invalid.other.example/{PROJECT}/-/issues/283",
            f"https://user:password@gitlab.example.invalid/{PROJECT}/-/issues/283",
            f"https://gitlab.example.invalid:8443/{PROJECT}/-/issues/283",
            "https://gitlab.example.invalid/group/../project/-/issues/283",
            f"https://gitlab.example.invalid/{PROJECT}/-/issues/0",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                resolve(url)


if __name__ == "__main__":
    unittest.main()
