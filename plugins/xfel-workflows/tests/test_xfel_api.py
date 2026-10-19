"""Offline checks for credential isolation and API mutation boundaries."""

from contextlib import redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError


spec = importlib.util.spec_from_file_location(
    "xfel_api", Path(__file__).parents[1] / "scripts" / "xfel_api.py"
)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.credentials = {
            "redmine_base_url": "https://redmine.example.invalid",
            "gitlab_base_url": "https://gitlab.example.invalid",
            "qdrant_base_url": "https://qdrant.example.invalid",
            "vllm_embedding_base_url": "https://embedding.example.invalid:8443/model/v1",
            "redmine_api_key": "personal-redmine",
            "gitlab_token": "personal-gitlab",
            "qdrant_api_key": "central-qdrant",
            "vllm_api_key": "embedding-only",
        }
        self.opener = MagicMock()
        response = self.opener.open.return_value.__enter__.return_value
        response.read.return_value = b'{"ok": true}'
        self.builder = patch.object(api, "build_opener", return_value=self.opener)
        self.builder.start()
        self.addCleanup(self.builder.stop)

    def test_private_file_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credentials.json"
            path.write_text(json.dumps(self.credentials))
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "chmod 600"):
                api.load_credentials(path)
            path.chmod(0o600)
            self.assertEqual(api.load_credentials(path), self.credentials)
            path.write_text('{"gitlab_token": "sensitive-broken-json"')
            with self.assertRaises(ValueError) as error:
                api.load_credentials(path)
            self.assertNotIn("sensitive-broken-json", str(error.exception))

    def test_credentials_scoped_to_service_hosts(self):
        for service, path, method, host, header, token in (
            ("redmine", "/issues/12.json", "GET", "redmine.example.invalid", "X-redmine-api-key", "personal-redmine"),
            ("gitlab", "/projects/Group%2FDevice", "GET", "gitlab.example.invalid", "Private-token", "personal-gitlab"),
            ("qdrant", "/collections", "GET", "qdrant.example.invalid", "Api-key", "central-qdrant"),
            ("embedding", "/embeddings", "POST", "embedding.example.invalid:8443", "Authorization", "Bearer embedding-only"),
        ):
            with self.subTest(service=service):
                self.assertEqual(api.request(service, method, path, self.credentials), {"ok": True})
                req = self.opener.open.call_args.args[0]
                self.assertEqual(req.host, host)
                self.assertEqual(req.get_header(header), token)
                self.assertEqual(len(req.headers), 2)

    def test_embedding_auth_optional_but_other_keys_required(self):
        api.request("embedding", "POST", "/embeddings", {
            "vllm_embedding_base_url": self.credentials["vllm_embedding_base_url"]
        })
        self.assertIsNone(self.opener.open.call_args.args[0].get_header("Authorization"))
        for service in ("redmine", "gitlab", "qdrant"):
            with self.assertRaisesRegex(ValueError, "credentials file"):
                api.request(service, "GET", "/", {
                    api.SERVICES[service][0]: self.credentials[api.SERVICES[service][0]]
                })

    def test_external_urls_and_unsupported_writes_rejected(self):
        for service, method, path in (
            ("gitlab", "GET", "https://other.example/projects"),
            ("gitlab", "GET", "//other.example/projects"),
            ("redmine", "POST", "/issues.json"),
            ("gitlab", "POST", "/projects/1/merge_requests/2/merge"),
            ("gitlab", "POST", "/projects/1/issues"),
            ("gitlab", "DELETE", "/projects/1/issues/283"),
            ("gitlab", "PUT", "/projects/1/issues/283/notes/9"),
            ("gitlab", "PUT", "/projects/1/issues/283/move"),
            ("gitlab", "PUT", "/projects/1/issues/0"),
            ("gitlab", "PUT", "/projects/1/issues/283?other=true"),
            ("gitlab", "POST", "/projects/1/issues/283/notes?other=true"),
            ("redmine", "PUT", "/projects/1/issues/283"),
            ("qdrant", "POST", "/collections/other/points/query"),
            ("qdrant", "PUT", "/collections/example"),
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                api.request(service, method, path, self.credentials)
        self.opener.open.assert_not_called()

    def test_missing_or_unsafe_base_urls_rejected_before_network(self):
        for value in (None, "", "http://gitlab.example.invalid", "https://user:secret@gitlab.example.invalid",
                      "https://gitlab.example.invalid?key=secret", "https://gitlab.example.invalid#fragment",
                      "https://gitlab.example.invalid:invalid", "https://gitlab.example.invalid\n"):
            credentials = dict(self.credentials, gitlab_base_url=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                api.request("gitlab", "GET", "/projects/1", credentials)
        self.opener.open.assert_not_called()

    def test_configured_base_paths_and_ports_preserved(self):
        credentials = dict(self.credentials, gitlab_base_url="https://gitlab.example.invalid:9443/gitlab/")
        api.request("gitlab", "GET", "/projects/1", credentials)
        req = self.opener.open.call_args.args[0]
        self.assertEqual(req.full_url, "https://gitlab.example.invalid:9443/gitlab/api/v4/projects/1")

    def test_mr_description_preserved_in_json_body(self):
        body = {"source_branch": "feature/device", "target_branch": "main",
                "title": "Device change", "description": "First line\n\nLiteral `code` and $values."}
        api.request("gitlab", "POST", "/projects/12/merge_requests", self.credentials, body)
        req = self.opener.open.call_args.args[0]
        self.assertEqual(json.loads(req.data), body)
        self.assertEqual(req.method, "POST")

    def test_both_qdrant_collections_support_read_only_posts(self):
        for name in api.COLLECTIONS:
            for operation in ("query", "scroll"):
                api.request("qdrant", "POST", f"/collections/{name}/points/{operation}",
                            self.credentials, {"limit": 2, "with_payload": True})

    def test_update_named_issue_preserves_only_supplied_fields(self):
        body = {"description": "Existing text\n\nRequested analysis: `code` and $values.",
                "add_labels": "needs-clarification"}
        path = "/projects/group%2Fintegration-requests/issues/283"
        api.request("gitlab", "PUT", path, self.credentials, body)
        req = self.opener.open.call_args.args[0]
        self.assertEqual(req.method, "PUT")
        self.assertEqual(req.full_url, "https://gitlab.example.invalid/api/v4" + path)
        self.assertEqual(json.loads(req.data), body)
        self.assertEqual(req.get_header("Private-token"), "personal-gitlab")

    def test_post_issue_note(self):
        body = {"body": "Requirements and questions\n\n- Specify units."}
        api.request("gitlab", "POST", "/projects/15335/issues/283/notes", self.credentials, body)
        req = self.opener.open.call_args.args[0]
        self.assertEqual(req.method, "POST")
        self.assertEqual(json.loads(req.data), body)

    def test_issue_writes_not_retried_after_uncertain_outcome(self):
        for method, path in (
            ("PUT", "/projects/15335/issues/283"),
            ("POST", "/projects/15335/issues/283/notes"),
        ):
            with self.subTest(method=method):
                self.opener.open.reset_mock()
                self.opener.open.side_effect = TimeoutError()
                with self.assertRaisesRegex(RuntimeError, "not retried"):
                    api.request("gitlab", method, path, self.credentials, {"body": "Analysis"})
                self.opener.open.assert_called_once()

    def test_redirects_rejected_and_failures_never_retried(self):
        self.assertIsNone(api.NoRedirect().redirect_request(
            None, None, 302, "Found", {}, "https://other.example"
        ))
        for error in (
            HTTPError("https://gitlab.example.invalid", 302, "sensitive", {}, io.BytesIO(b"secret")),
            URLError("sensitive diagnostic"), TimeoutError("sensitive diagnostic"),
        ):
            with self.subTest(error=type(error).__name__):
                self.opener.open.reset_mock()
                self.opener.open.side_effect = error
                with self.assertRaises(RuntimeError) as raised:
                    api.request("gitlab", "POST", "/projects/1/merge_requests", self.credentials, {})
                self.opener.open.assert_called_once()
                self.assertNotIn("sensitive", str(raised.exception))
                self.assertNotIn("secret", str(raised.exception))

    def test_cli_missing_file_returns_failure_without_network(self):
        with patch("sys.argv", ["xfel_api.py", "gitlab", "GET", "/user",
                                "--credentials-file", "/nonexistent/xfel-credentials.json"]):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(api.main(), 1)
        self.opener.open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
