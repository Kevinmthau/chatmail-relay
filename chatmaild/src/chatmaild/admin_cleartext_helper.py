"""Helper for toggling plaintext inbound/outbound mail per account as vmail.

This is invoked by the CGI wrapper via sudo so maildir marker files are
created/removed with the correct ownership/permissions.
"""

from __future__ import annotations

import json
import sys

from chatmaild.config import Config, read_config

CONFIG_PATH = "/usr/local/lib/chatmaild/chatmail.ini"
MAX_BODY_LEN = 4096

INCOMING_ENFORCE_MARKER = "enforceE2EEincoming"
OUTGOING_ALLOW_MARKER = "allowCleartextOutgoing"


def _parse_enabled(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "on"):
            return True
        if v in ("0", "false", "no", "off"):
            return False
    return None


def set_cleartext_mode(config: Config, *, email: str, enabled) -> tuple[int, dict]:
    email = (email or "").strip()
    if not email:
        return 400, {"error": "email is required"}
    if not email.endswith(f"@{config.mail_domain}"):
        return 400, {"error": f"email must end with @{config.mail_domain}"}

    enabled_bool = _parse_enabled(enabled)
    if enabled_bool is None:
        return 400, {"error": "enabled must be a boolean"}

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

    pw_path = maildir.joinpath("password")
    try:
        st = pw_path.stat()
    except FileNotFoundError:
        return 404, {"error": "account not found"}
    if st.st_size <= 0:
        return 404, {"error": "account not found"}

    incoming_path = maildir.joinpath(INCOMING_ENFORCE_MARKER)
    outgoing_path = maildir.joinpath(OUTGOING_ALLOW_MARKER)

    if enabled_bool:
        # Allow inbound cleartext by removing marker, and allow outbound cleartext.
        try:
            incoming_path.unlink()
        except FileNotFoundError:
            pass
        outgoing_path.touch(exist_ok=True)
    else:
        # Enforce inbound encryption and disallow outbound cleartext.
        incoming_path.touch(exist_ok=True)
        try:
            outgoing_path.unlink()
        except FileNotFoundError:
            pass

    incoming_cleartext = not incoming_path.exists()
    outgoing_cleartext = outgoing_path.exists()

    return (
        200,
        {
            "status": "updated",
            "email": email,
            "enabled": enabled_bool,
            "incoming_cleartext": incoming_cleartext,
            "outgoing_cleartext": outgoing_cleartext,
        },
    )


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
    status_code, body = set_cleartext_mode(
        config, email=payload.get("email"), enabled=payload.get("enabled")
    )
    print(json.dumps({"status_code": status_code, **body}))


if __name__ == "__main__":
    main()

