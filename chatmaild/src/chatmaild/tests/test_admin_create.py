import chatmaild.doveauth
from chatmaild.admin_create import create_admin_account


def test_create_admin_account_success(example_config):
    status_code, payload = create_admin_account(
        example_config, "abcd12345@chat.example.org", "qwertyui9"
    )
    assert status_code == 201
    assert payload["status"] == "created"


def test_create_admin_account_rejects_wrong_domain(example_config):
    status_code, payload = create_admin_account(
        example_config, "abcd12345@example.com", "qwertyui9"
    )
    assert status_code == 400
    assert "must end with" in payload["error"]


def test_create_admin_account_rejects_existing(example_config):
    addr = "abcd12345@chat.example.org"
    create_admin_account(example_config, addr, "qwertyui9")
    status_code, payload = create_admin_account(example_config, addr, "qwertyui9")
    assert status_code == 409
    assert payload["error"] == "account already exists"


def test_create_admin_account_rejects_short_password(example_config):
    status_code, payload = create_admin_account(
        example_config, "abcd12345@chat.example.org", "short"
    )
    assert status_code == 400
    assert payload["error"] == "account creation policy check failed"


def test_create_admin_account_ignores_nocreate(monkeypatch, tmp_path, example_config):
    no_create = tmp_path.joinpath("nocreate")
    no_create.write_text("")
    monkeypatch.setattr(chatmaild.doveauth, "NOCREATE_FILE", str(no_create))

    status_code, payload = create_admin_account(
        example_config, "abcd12345@chat.example.org", "qwertyui9"
    )
    assert status_code == 201
    assert payload["status"] == "created"
