import base64
import time

from chatmaild.admin_create import create_admin_account
from chatmaild.doveauth import encrypt_password
from chatmaild.events import (
    EventBus,
    SlidingWindowRateLimiter,
    _authenticate_local_user,
    _parse_basic_auth,
    _verify_password,
)


def _basic_auth(email: str, password: str) -> str:
    token = base64.b64encode(f"{email}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def test_parse_basic_auth():
    auth = _basic_auth("ab@chat.example.org", "qwertyui9")
    user, pw = _parse_basic_auth(auth)
    assert user == "ab@chat.example.org"
    assert pw == "qwertyui9"


def test_verify_password():
    enc_password = encrypt_password("qwertyui9")
    assert _verify_password("qwertyui9", enc_password)
    assert not _verify_password("wrong-password", enc_password)


def test_authenticate_local_user(example_config):
    create_admin_account(example_config, "ab@chat.example.org", "qwertyui9")
    auth = _basic_auth("ab@chat.example.org", "qwertyui9")
    user, err = _authenticate_local_user(example_config, auth)
    assert user == "ab@chat.example.org"
    assert err is None


def test_event_bus_publish():
    bus = EventBus(queue_size=2)
    client_id, q = bus.register("xy@chat.example.org")
    event = {"event": "typing", "from": "ab@chat.example.org"}
    delivered = bus.publish("xy@chat.example.org", event)
    assert delivered == 1
    assert q.get(timeout=1) == event
    bus.unregister("xy@chat.example.org", client_id)


def test_rate_limiter():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=1)
    assert limiter.allow("ab@chat.example.org")
    assert limiter.allow("ab@chat.example.org")
    assert not limiter.allow("ab@chat.example.org")
    time.sleep(1.05)
    assert limiter.allow("ab@chat.example.org")
