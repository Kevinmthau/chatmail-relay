"""Helper for creating accounts as the vmail user.

This is invoked by the CGI wrapper via sudo so new maildirs and password files
are created with the correct ownership.
"""

import json
import sys

from chatmaild.admin_create import create_admin_account
from chatmaild.config import read_config

CONFIG_PATH = "/usr/local/lib/chatmaild/chatmail.ini"
MAX_BODY_LEN = 4096


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

    email = payload.get("email")
    password = payload.get("password")

    config = read_config(CONFIG_PATH)
    status_code, body = create_admin_account(config, email=email, password=password)
    print(json.dumps({"status_code": status_code, **body}))


if __name__ == "__main__":
    main()
