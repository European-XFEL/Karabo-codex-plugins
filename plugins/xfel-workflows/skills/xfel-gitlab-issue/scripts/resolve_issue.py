#!/usr/bin/env python3
"""Resolve an XFEL GitLab issue URL or selected board card without network access."""

import argparse
import base64
import binascii
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, quote, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from xfel_api import load_credentials, service_base_url


def resolve_issue(url, gitlab_base_url):
    base = urlsplit(gitlab_base_url)
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname != base.hostname
            or (parts.port or 443) != (base.port or 443) or parts.username or parts.password
            or not parts.path.startswith(base.path.rstrip("/") + "/")):
        raise ValueError("Use an issue or board URL under the configured GitLab base URL.")
    relative_path = parts.path[len(base.path.rstrip("/")):]
    match = re.fullmatch(r"/(.+)/-/(?:issues|work_items)/([1-9][0-9]*)/?", relative_path)
    if match:
        project, iid = unquote(match[1]), match[2]
    else:
        match = re.fullmatch(r"/(.+)/-/boards(?:/[0-9]+)?/?", relative_path)
        if not match:
            raise ValueError("Expected an issue URL or board URL with a selected issue.")
        selections = parse_qs(parts.query).get("show", [])
        if len(selections) != 1:
            raise ValueError("Board URL must contain exactly one show selection.")
        try:
            encoded = selections[0]
            selection = json.loads(base64.b64decode(
                encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
            ))
        except (ValueError, UnicodeError, binascii.Error):
            raise ValueError("Board selection must be base64-encoded JSON.") from None
        if not isinstance(selection, dict):
            raise ValueError("Board selection must identify a project and issue IID.")
        project, iid = selection.get("full_path"), str(selection.get("iid", ""))
        if not isinstance(project, str) or project.casefold() != unquote(match[1]).casefold():
            raise ValueError("Selected issue project does not match the board project.")
    if (not re.fullmatch(r"[1-9][0-9]*", iid) or "/" not in project
            or any(not segment or segment in (".", "..") for segment in project.split("/"))):
        raise ValueError("Expected a namespace/project path and a positive issue IID.")
    return {
        "project_path": project,
        "iid": int(iid),
        "api_path": f"/projects/{quote(project, safe='')}/issues/{iid}",
        "web_url": f"{gitlab_base_url.rstrip('/')}/{quote(project, safe='/')}/-/issues/{iid}",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--credentials-file", type=Path)
    args = parser.parse_args()
    try:
        credentials = load_credentials(args.credentials_file)
        print(json.dumps(resolve_issue(args.url, service_base_url("gitlab", credentials)), indent=2))
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
