import requests

from cmdeploy.genqr import gen_qr_png_data


def test_gen_qr_png_data(maildomain):
    data = gen_qr_png_data(maildomain)
    assert data


def test_fastcgi_working(maildomain, chatmail_config):
    url = f"https://{maildomain}/new"
    print(url)
    res = requests.post(url)
    if chatmail_config.public_create_enabled:
        assert maildomain in res.json().get("email")
        assert len(res.json().get("password")) > chatmail_config.password_min_length
    else:
        assert res.status_code == 404


def test_newemail_configure(maildomain, rpc, chatmail_config):
    """Test configuring accounts by scanning a QR code works."""
    # Invite QR codes depend on /new being enabled.
    if not chatmail_config.public_create_enabled:
        import pytest

        pytest.skip("public account creation disabled (/new is off)")

    url = f"DCACCOUNT:https://{maildomain}/new"
    for i in range(3):
        account_id = rpc.add_account()
        rpc.set_config_from_qr(account_id, url)
        rpc.configure(account_id)
