#!/usr/bin/env python3
"""Small, credential-file-backed client for the XFEL workflow skills."""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


SERVICES = {
    "redmine": ("redmine_base_url", "redmine_api_key", "X-Redmine-API-Key"),
    "gitlab": ("gitlab_base_url", "gitlab_token", "PRIVATE-TOKEN"),
    "qdrant": ("qdrant_base_url", "qdrant_api_key", "api-key"),
    "embedding": (
        "vllm_embedding_base_url", "vllm_api_key", "Authorization"
    ),
}
COLLECTIONS = (
    "code_karabodevices3_project_summaries",
    "docs_gitlab_karaboDevices3_summaries",
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_credentials(path=None):
    path = Path(path or os.environ.get(
        "XFEL_CREDENTIALS_FILE", "~/.config/xfel/credentials.json"
    )).expanduser()
    with path.open(encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError("Credentials must be a private regular file (chmod 600).")
        if info.st_uid != os.getuid():
            raise ValueError("Credentials must be owned by the current user.")
        try:
            credentials = json.load(stream)
        except json.JSONDecodeError:
            raise ValueError("Credentials file must contain a JSON object.") from None
    if not isinstance(credentials, dict):
        raise ValueError("Credentials file must contain a JSON object.")
    return credentials


def service_base_url(service, credentials):
    key = SERVICES[service][0]
    value = credentials.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Set {key} in the credentials file.")
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == "https" and parts.hostname and parts.port != 0
                 and not parts.username and not parts.password
                 and not parts.query and not parts.fragment
                 and not any(character.isspace() for character in value))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"{key} must be an HTTPS base URL without credentials, query, or fragment.")
    return value.rstrip("/")


def request(service, method, path, credentials, data=None):
    _, key, header = SERVICES[service]
    base = service_base_url(service, credentials)
    if service == "gitlab":
        base += "/api/v4"
    parts = urlsplit(path)
    if (not path.startswith("/") or path.startswith("//") or parts.scheme
            or parts.netloc or parts.fragment):
        raise ValueError("Use an API path starting with a single slash, not a URL.")
    allowed = method == "GET" and service in ("redmine", "gitlab", "qdrant")
    if method == "POST":
        allowed = (
            (service == "gitlab" and re.fullmatch(r"/projects/[^/]+/merge_requests", path))
            or (service == "gitlab" and re.fullmatch(
                r"/projects/[^/]+/issues/[1-9][0-9]*/notes", path
            ))
            or (service == "qdrant" and parts.path in {
                f"/collections/{name}/points/{operation}"
                for name in COLLECTIONS for operation in ("query", "scroll")
            })
            or (service == "embedding" and path == "/embeddings")
        )
    if method == "PUT":
        allowed = service == "gitlab" and re.fullmatch(
            r"/projects/[^/]+/issues/[1-9][0-9]*", path
        )
    if not allowed:
        raise ValueError("Only reads, embeddings, GitLab MR creation, and issue updates/notes are supported.")
    token = credentials.get(key, "")
    if not isinstance(token, str) or (not token.strip() and service != "embedding"):
        raise ValueError(f"Set {key} in the credentials file.")
    if "\r" in token or "\n" in token:
        raise ValueError(f"Invalid {key} in the credentials file.")
    headers = {"Accept": "application/json"}
    if token:
        headers[header] = f"Bearer {token}" if service == "embedding" else token
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(base + path, data=body, headers=headers, method=method)
    try:
        with build_opener(NoRedirect()).open(req, timeout=60) as response:
            return json.load(response)
    except HTTPError as error:
        # Response bodies may echo credentials or confidential request content.
        raise RuntimeError(f"{service}: HTTP {error.code}; request not retried.") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError(f"{service}: connection failed; request not retried.") from None
    except (ValueError, UnicodeError):
        raise RuntimeError(f"{service}: expected a JSON response; request not retried.") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=SERVICES)
    parser.add_argument("method", choices=("GET", "POST", "PUT"))
    parser.add_argument("path", help="API path; quote query strings and URL-encode values")
    parser.add_argument("--data-file", type=Path, help="JSON request body; never credentials")
    parser.add_argument("--credentials-file", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.data_file.read_text()) if args.data_file else None
        result = request(args.service, args.method, args.path,
                         load_credentials(args.credentials_file), data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
