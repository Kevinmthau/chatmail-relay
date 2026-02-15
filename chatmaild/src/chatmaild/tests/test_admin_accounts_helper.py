from chatmaild.admin_accounts_helper import list_accounts
from chatmaild.admin_create import create_admin_account


def test_list_accounts_includes_created_accounts(example_config):
    create_admin_account(example_config, "ab@chat.example.org", "qwertyui9")
    create_admin_account(example_config, "xy@chat.example.org", "qwertyui9")

    accounts = list_accounts(example_config)
    emails = [a["email"] for a in accounts]

    assert emails == sorted(emails)
    assert "ab@chat.example.org" in emails
    assert "xy@chat.example.org" in emails
    assert all(isinstance(a.get("last_login"), int) for a in accounts)
    assert all(isinstance(a.get("incoming_cleartext"), bool) for a in accounts)
    assert all(isinstance(a.get("outgoing_cleartext"), bool) for a in accounts)
    # New accounts default to strict mode.
    assert all(a.get("incoming_cleartext") is False for a in accounts)
    assert all(a.get("outgoing_cleartext") is False for a in accounts)


def test_list_accounts_skips_entries_without_password(example_config):
    example_config.mailboxes_dir.joinpath("nopw@chat.example.org").mkdir(parents=True)
    create_admin_account(example_config, "ab@chat.example.org", "qwertyui9")

    accounts = list_accounts(example_config)
    emails = [a["email"] for a in accounts]
    assert "nopw@chat.example.org" not in emails
