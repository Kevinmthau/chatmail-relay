"""Helper for listing accounts as the vmail user.

This is invoked by the CGI wrapper via sudo so mailbox directories and password
files can be read with the correct permissions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from chatmaild.config import Config, read_config

CONFIG_PATH = "/usr/local/lib/chatmaild/chatmail.ini"

INCOMING_ENFORCE_MARKER = "enforceE2EEincoming"
OUTGOING_ALLOW_MARKER = "allowCleartextOutgoing"


def list_accounts(
    config: Config, *, limit: Optional[int] = None
) -> list[dict[str, Any]]:
    """Return a list of existing accounts.

    An account is considered to exist if a non-empty "password" file is present.
    """

    base: Path = config.mailboxes_dir
    if not base.exists():
        return []

    domain_suffix = f"@{config.mail_domain}"

    accounts: list[dict[str, Any]] = []
    for entry in sorted(base.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue

        addr = entry.name
        if "@" not in addr:
            continue
        if not addr.endswith(domain_suffix):
            # Safety guard: mailboxes_dir should only contain this domain.
            continue

        pw_path = entry.joinpath("password")
        try:
            st = pw_path.stat()
        except FileNotFoundError:
            continue

        if st.st_size <= 0:
            continue

        incoming_cleartext = not entry.joinpath(INCOMING_ENFORCE_MARKER).exists()
        outgoing_cleartext = entry.joinpath(OUTGOING_ALLOW_MARKER).exists()

        accounts.append(
            {
                "email": addr,
                "last_login": int(st.st_mtime),
                "incoming_cleartext": incoming_cleartext,
                "outgoing_cleartext": outgoing_cleartext,
            }
        )
        if limit is not None and len(accounts) >= limit:
            break

    return accounts


def main() -> None:
    config = read_config(CONFIG_PATH)
    accounts = list_accounts(config)
    print(
        json.dumps(
            {"status": "ok", "count": len(accounts), "accounts": accounts},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
