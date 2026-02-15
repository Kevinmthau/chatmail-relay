"""Helper for setting account passwords as the vmail user.

This is invoked by the CGI wrapper via sudo so password files are written with
the correct ownership.
"""

from __future__ import annotations

import json
import sys

from chatmaild.config import Config, read_config
from chatmaild.doveauth import encrypt_password

CONFIG_PATH = "/usr/local/lib/chatmaild/chatmail.ini"
MAX_BODY_LEN = 4096


def set_admin_password(config: Config, email: str, password: str):
    email = (email or "").strip()
    password = password or ""

    if not email or not password:
        return 400, {"error": "email and password are required"}

    if not email.endswith(f"@{config.mail_domain}"):
        return 400, {"error": f"email must end with @{config.mail_domain}"}

    try:
        user = config.get_user(email)
    except ValueError:
        return 400, {"error": "invalid email format"}

    if len(password) < config.password_min_length:
        return 400, {
            "error": f"password must be at least {config.password_min_length} characters"
        }

    # Avoid accidentally creating new accounts via the password endpoint.
    if not user.get_userdb_dict():
        return 404, {"error": "account not found"}

    user.set_password(encrypt_password(password))
    return 200, {"status": "password-updated", "email": email}


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
    status_code, body = set_admin_password(
        config,
        email=payload.get("email"),
        password=payload.get("password"),
    )
    print(json.dumps({"status_code": status_code, **body}))


if __name__ == "__main__":
    main()

