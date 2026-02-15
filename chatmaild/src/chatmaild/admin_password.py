#!/usr/local/lib/chatmaild/venv/bin/python3

"""CGI script for setting an account password through an admin endpoint."""

import json
import os
import subprocess
import sys
from urllib.parse import parse_qs

MAX_BODY_LEN = 4096
HELPER_BIN = "/usr/local/lib/chatmaild/venv/bin/chatmail-admin-password-helper"


def parse_body():
    method = os.environ.get("REQUEST_METHOD", "").upper()
    if method != "POST":
        return None, (405, {"error": "method not allowed"})

    content_length = int(os.environ.get("CONTENT_LENGTH") or "0")
    if content_length > MAX_BODY_LEN:
        return None, (413, {"error": "request body too large"})

    raw_body = sys.stdin.read(content_length) if content_length else ""
    ctype = os.environ.get("CONTENT_TYPE", "")

    if "application/json" in ctype:
        try:
            payload = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            return None, (400, {"error": "invalid json payload"})
        return payload, None

    params = parse_qs(raw_body, keep_blank_values=True)
    payload = {
        "email": params.get("email", [""])[0],
        "password": params.get("password", [""])[0],
    }
    return payload, None


def print_response(status_code: int, payload: dict):
    print(f"Status: {status_code}")
    print("Content-Type: application/json")
    print("")
    print(json.dumps(payload))


def main():
    payload, parse_error = parse_body()
    if parse_error:
        print_response(*parse_error)
        return

    # This CGI runs under fcgiwrap as www-data. Updating password must be done
    # as vmail so permissions/ownership match the rest of the system.
    req = json.dumps(payload)
    proc = subprocess.run(
        ["sudo", "-n", "-u", "vmail", HELPER_BIN],
        input=req,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )

    raw = (proc.stdout or "").strip()
    if not raw:
        print_response(
            500,
            {
                "error": "password helper failed",
                "stderr": (proc.stderr or "").strip(),
            },
        )
        return

    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        print_response(500, {"error": "invalid helper response", "raw": raw})
        return

    status_code = int(body.pop("status_code", 500))
    print_response(status_code, body)


if __name__ == "__main__":
    main()

