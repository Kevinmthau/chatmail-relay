#!/usr/local/lib/chatmaild/venv/bin/python3

"""CGI script for creating accounts through an admin endpoint."""

import json
import os
import sys
from urllib.parse import parse_qs

from chatmaild.config import Config, read_config
from chatmaild.doveauth import encrypt_password, is_allowed_to_create

CONFIG_PATH = "/usr/local/lib/chatmaild/chatmail.ini"
MAX_BODY_LEN = 4096


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

    if not is_allowed_to_create(config, email, password):
        return 400, {"error": "account creation policy check failed"}

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

    config = read_config(CONFIG_PATH)
    status_code, payload = create_admin_account(config, email=email, password=password)
    print_response(status_code, payload)


if __name__ == "__main__":
    main()
