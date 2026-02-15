"""Wrapper used by systemd to start filtermail with dynamic passthrough senders.

Why:
  - `passthrough_senders` lives in chatmail.ini, which is overwritten by cmdeploy.
  - For "plaintext opt-in" mailboxes we need a persistent per-mailbox setting.

How:
  - Admin endpoint toggles a marker file in the mailbox directory:
      allowCleartextOutgoing
  - On filtermail service start, this wrapper scans all mailboxes for that marker,
    patches `passthrough_senders` in a runtime copy of chatmail.ini, and then
    exec()s the real filtermail binary.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

from chatmaild.config import Config, read_config

OUTGOING_ALLOW_MARKER = "allowCleartextOutgoing"

DEFAULT_RUNTIME_DIR = Path("/run/chatmail-filtermail")


def scan_allow_cleartext_outgoing(config: Config) -> set[str]:
    base: Path = config.mailboxes_dir
    if not base.exists():
        return set()

    suffix = f"@{config.mail_domain}"
    out: set[str] = set()
    for entry in sorted(base.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        addr = entry.name
        if "@" not in addr or not addr.endswith(suffix):
            continue
        if entry.joinpath(OUTGOING_ALLOW_MARKER).exists():
            out.add(addr)
    return out


def _is_section_header(line: str) -> bool:
    st = line.strip()
    return st.startswith("[") and st.endswith("]") and len(st) >= 3


def patch_params_key(text: str, *, key: str, value: str) -> str:
    """Replace/insert `key = value` within [params] section, preserving comments."""

    lines = text.splitlines(keepends=True)
    newline = "\r\n" if any(l.endswith("\r\n") for l in lines) else "\n"

    in_params = False
    key_re = re.compile(
        rf"^(\s*){re.escape(key)}\s*=\s*([^\r\n#]*?)(\s*#.*)?(\r?\n)?$"
    )

    for i, line in enumerate(lines):
        if _is_section_header(line):
            in_params = line.strip() == "[params]"
            continue
        if not in_params:
            continue
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        m = key_re.match(line)
        if not m:
            continue
        indent = m.group(1) or ""
        comment = m.group(3) or ""
        eol = m.group(4) or newline
        lines[i] = f"{indent}{key} = {value}{comment}{eol}"
        return "".join(lines)

    # Insert missing key before the next section header (or EOF).
    insert_at = None
    in_params = False
    for i, line in enumerate(lines):
        if _is_section_header(line):
            if in_params:
                insert_at = i
                break
            in_params = line.strip() == "[params]"
    if insert_at is None:
        if in_params:
            insert_at = len(lines)
        else:
            # No [params] section; append a minimal one.
            if lines and not lines[-1].endswith(("\n", "\r\n")):
                lines.append(newline)
            lines.append(f"[params]{newline}")
            insert_at = len(lines)

    lines.insert(insert_at, f"{key} = {value}{newline}")
    return "".join(lines)


def build_runtime_ini_text(config_path: Path, *, passthrough_senders: list[str]) -> str:
    base_text = config_path.read_text(encoding="utf-8")
    value = " ".join(passthrough_senders)
    return patch_params_key(base_text, key="passthrough_senders", value=value)


def compute_passthrough_senders(config: Config) -> list[str]:
    base = set(config.passthrough_senders)
    dynamic = scan_allow_cleartext_outgoing(config)
    merged = sorted(base | dynamic)
    return merged


def _runtime_dir() -> Path:
    override = os.environ.get("CHATMAIL_FILTERMAIL_RUNTIME_DIR", "").strip()
    if override:
        return Path(override)
    return DEFAULT_RUNTIME_DIR


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3:
        print(
            "usage: chatmail-filtermail-wrapper FILTERMAIL_BIN CHATMAIL_INI MODE",
            file=sys.stderr,
        )
        return 2

    filtermail_bin, config_path_raw, mode = argv
    if mode not in ("outgoing", "incoming"):
        print("MODE must be 'outgoing' or 'incoming'", file=sys.stderr)
        return 2

    config_path = Path(config_path_raw)
    runtime_dir = _runtime_dir()
    runtime_path = runtime_dir.joinpath(f"{mode}.ini")

    try:
        config = read_config(config_path)
        passthrough_senders = compute_passthrough_senders(config)
        patched = build_runtime_ini_text(config_path, passthrough_senders=passthrough_senders)

        runtime_dir.mkdir(parents=True, exist_ok=True)
        tmp = runtime_path.with_name(runtime_path.name + ".tmp")
        tmp.write_text(patched, encoding="utf-8")
        tmp.replace(runtime_path)
    except Exception:
        logging.exception("failed to build runtime filtermail config, falling back")
        runtime_path = config_path

    os.execv(filtermail_bin, [filtermail_bin, str(runtime_path), mode])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

