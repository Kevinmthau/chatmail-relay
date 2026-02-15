from pathlib import Path

from chatmaild.config import read_config
from chatmaild.filtermail_wrapper import (
    OUTGOING_ALLOW_MARKER,
    build_runtime_ini_text,
    compute_passthrough_senders,
)


def test_filtermail_wrapper_merges_dynamic_passthrough_senders(make_config, tmp_path):
    config = make_config(
        "chat.example.org",
        settings={"passthrough_senders": "legacy@chat.example.org"},
    )

    # Simulate admin enabling plaintext for a mailbox.
    mbox = config.mailboxes_dir.joinpath("ab@chat.example.org")
    mbox.mkdir(parents=True, exist_ok=True)
    mbox.joinpath(OUTGOING_ALLOW_MARKER).touch()

    merged = compute_passthrough_senders(config)
    assert merged == ["ab@chat.example.org", "legacy@chat.example.org"]

    patched_text = build_runtime_ini_text(Path(config._inipath), passthrough_senders=merged)
    patched_path = tmp_path.joinpath("patched.ini")
    patched_path.write_text(patched_text)

    cfg2 = read_config(patched_path)
    assert cfg2.passthrough_senders == merged

