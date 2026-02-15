from chatmaild.admin_create import create_admin_account
from chatmaild.admin_password_helper import set_admin_password


def test_set_admin_password_success(example_config):
    addr = "abcd12345@chat.example.org"
    status_code, _payload = create_admin_account(example_config, addr, "qwertyui9")
    assert status_code == 201

    user = example_config.get_user(addr)
    old_pw = user.password_path.read_text()

    status_code, payload = set_admin_password(example_config, addr, "newpassw0rd!")
    assert status_code == 200
    assert payload["status"] == "password-updated"
    assert payload["email"] == addr

    new_pw = user.password_path.read_text()
    assert new_pw != old_pw


def test_set_admin_password_rejects_wrong_domain(example_config):
    status_code, payload = set_admin_password(
        example_config, "abcd12345@example.com", "newpassw0rd!"
    )
    assert status_code == 400
    assert "must end with" in payload["error"]


def test_set_admin_password_rejects_missing_account(example_config):
    status_code, payload = set_admin_password(
        example_config, "abcd12345@chat.example.org", "newpassw0rd!"
    )
    assert status_code == 404
    assert payload["error"] == "account not found"


def test_set_admin_password_rejects_short_password(example_config):
    addr = "abcd12345@chat.example.org"
    status_code, _payload = create_admin_account(example_config, addr, "qwertyui9")
    assert status_code == 201

    status_code, payload = set_admin_password(example_config, addr, "short")
    assert status_code == 400
    assert "password must be at least" in payload["error"]

