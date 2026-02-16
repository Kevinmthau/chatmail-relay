#!/usr/local/lib/chatmaild/venv/bin/python3

"""CGI script for creating accounts through an admin endpoint."""

import json
import os
import subprocess
import sys
from urllib.parse import parse_qs

from chatmaild.config import Config
from chatmaild.doveauth import encrypt_password, is_allowed_to_create

CONFIG_PATH = "/usr/local/lib/chatmaild/chatmail.ini"
MAX_BODY_LEN = 4096
HELPER_BIN = "/usr/local/lib/chatmaild/venv/bin/chatmail-admin-create-helper"


def create_admin_account(config: Config, email: str, password: str):
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

    if user.get_userdb_dict():
        return 409, {"error": "account already exists"}

    if not is_allowed_to_create(config, email, password, ignore_nocreate=True):
        return 400, {"error": "account creation policy check failed"}

    user.set_email_friendly_defaults()
    user.set_password(encrypt_password(password))
    return 201, {"status": "created", "email": email}


def parse_body():
    method = os.environ.get("REQUEST_METHOD", "").upper()
    if method != "POST":
        return None, None, (405, {"error": "method not allowed"})

    content_length = int(os.environ.get("CONTENT_LENGTH") or "0")
    if content_length > MAX_BODY_LEN:
        return None, None, (413, {"error": "request body too large"})

    raw_body = sys.stdin.read(content_length) if content_length else ""
    ctype = os.environ.get("CONTENT_TYPE", "")

    if "application/json" in ctype:
        try:
            payload = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            return None, None, (400, {"error": "invalid json payload"})
        return payload.get("email"), payload.get("password"), None

    params = parse_qs(raw_body, keep_blank_values=True)
    return params.get("email", [""])[0], params.get("password", [""])[0], None


def print_response(status_code: int, payload: dict):
    print(f"Status: {status_code}")
    print("Content-Type: application/json")
    print("")
    print(json.dumps(payload))


def main():
    email, password, parse_error = parse_body()
    if parse_error:
        print_response(*parse_error)
        return

    # This CGI runs under fcgiwrap as www-data. Creating a mailbox dir must be done
    # as vmail so permissions/ownership match the rest of the system.
    req = json.dumps({"email": email, "password": password})
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
                "error": "account helper failed",
                "stderr": (proc.stderr or "").strip(),
            },
        )
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print_response(500, {"error": "invalid helper response", "raw": raw})
        return

    status_code = int(payload.pop("status_code", 500))
    print_response(status_code, payload)


if __name__ == "__main__":
    main()
