"""Helper for deleting accounts as the vmail user.

This is invoked by the CGI wrapper via sudo so maildir deletion happens with
the correct ownership/permissions.
"""

from __future__ import annotations

import json
import shutil
import sys

from chatmaild.config import Config, read_config

CONFIG_PATH = "/usr/local/lib/chatmaild/chatmail.ini"
MAX_BODY_LEN = 4096


def delete_admin_account(config: Config, email: str):
    email = (email or "").strip()
    if not email:
        return 400, {"error": "email is required"}
    if not email.endswith(f"@{config.mail_domain}"):
        return 400, {"error": f"email must end with @{config.mail_domain}"}

    try:
        user = config.get_user(email)
    except ValueError:
        return 400, {"error": "invalid email format"}

    maildir = user.maildir
    # Safety guard: ensure the target is under the configured mailboxes_dir.
    try:
        maildir.relative_to(config.mailboxes_dir)
    except ValueError:
        return 400, {"error": "invalid mailbox path"}

    if not maildir.exists():
        return 404, {"error": "account not found"}

    shutil.rmtree(maildir)
    return 200, {"status": "deleted", "email": email}


def _read_json_stdin() -> dict:
    raw = sys.stdin.read(MAX_BODY_LEN + 1)
    if len(raw) > MAX_BODY_LEN:
        return {"_error": (413, {"error": "request body too large"})}
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {"_error": (400, {"error": "invalid json payload"})}
    return payload


def main() -> None:
    payload = _read_json_stdin()
    if "_error" in payload:
        status_code, body = payload["_error"]
        print(json.dumps({"status_code": status_code, **body}))
        return

    config = read_config(CONFIG_PATH)
    status_code, body = delete_admin_account(config, email=payload.get("email"))
    print(json.dumps({"status_code": status_code, **body}))


if __name__ == "__main__":
    main()

