from chatmaild.admin_cleartext_helper import (
    INCOMING_ENFORCE_MARKER,
    OUTGOING_ALLOW_MARKER,
    set_cleartext_mode,
)
from chatmaild.admin_create import create_admin_account


def test_cleartext_toggle_enable_disable(example_config):
    create_admin_account(example_config, "ab@chat.example.org", "qwertyui9")
    maildir = example_config.mailboxes_dir.joinpath("ab@chat.example.org")

    assert not maildir.joinpath(INCOMING_ENFORCE_MARKER).exists()
    assert maildir.joinpath(OUTGOING_ALLOW_MARKER).exists()

    status, body = set_cleartext_mode(
        example_config, email="ab@chat.example.org", enabled=True
    )
    assert status == 200
    assert body["incoming_cleartext"] is True
    assert body["outgoing_cleartext"] is True
    assert not maildir.joinpath(INCOMING_ENFORCE_MARKER).exists()
    assert maildir.joinpath(OUTGOING_ALLOW_MARKER).exists()

    status, body = set_cleartext_mode(
        example_config, email="ab@chat.example.org", enabled=False
    )
    assert status == 200
    assert body["incoming_cleartext"] is False
    assert body["outgoing_cleartext"] is False
    assert maildir.joinpath(INCOMING_ENFORCE_MARKER).exists()
    assert not maildir.joinpath(OUTGOING_ALLOW_MARKER).exists()


def test_cleartext_toggle_missing_account_returns_404(example_config):
    status, body = set_cleartext_mode(
        example_config, email="missing@chat.example.org", enabled=True
    )
    assert status == 404
    assert body["error"] == "account not found"


def test_cleartext_toggle_rejects_wrong_domain(example_config):
    status, body = set_cleartext_mode(example_config, email="ab@elsewhere.org", enabled=True)
    assert status == 400
    assert body["error"].startswith("email must end with @")
