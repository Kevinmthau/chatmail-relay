"""Relay-mediated realtime event service (SSE + authenticated event POST)."""

from __future__ import annotations

import base64
import json
import logging
import queue
import re
import sys
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlsplit

try:
    import crypt_r
except ImportError:
    import crypt as crypt_r

from .config import Config, read_config

MAX_BODY_LEN = 4096
STREAM_PATH = "/events/stream"
SEND_PATH = "/events/send"
EVENT_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
PASSWORD_PREFIX = "{SHA512-CRYPT}"


class EventBus:
    """In-memory per-address fanout queues."""

    def __init__(self, *, queue_size: int = 128):
        self._queue_size = queue_size
        self._lock = Lock()
        self._queues: dict[str, dict[int, queue.Queue]] = {}
        self._next_id = 0

    def register(self, addr: str) -> tuple[int, queue.Queue]:
        with self._lock:
            self._next_id += 1
            client_id = self._next_id
            addr_queues = self._queues.setdefault(addr, {})
            q: queue.Queue = queue.Queue(maxsize=self._queue_size)
            addr_queues[client_id] = q
            return client_id, q

    def unregister(self, addr: str, client_id: int) -> None:
        with self._lock:
            addr_queues = self._queues.get(addr)
            if not addr_queues:
                return
            addr_queues.pop(client_id, None)
            if not addr_queues:
                self._queues.pop(addr, None)

    def publish(self, addr: str, event: dict) -> int:
        with self._lock:
            addr_queues = list(self._queues.get(addr, {}).values())

        delivered = 0
        for q in addr_queues:
            try:
                q.put_nowait(event)
                delivered += 1
                continue
            except queue.Full:
                pass

            # Keep newest event if queue is full.
            try:
                q.get_nowait()
            except queue.Empty:
                pass
            try:
                q.put_nowait(event)
                delivered += 1
            except queue.Full:
                pass
        return delivered


class SlidingWindowRateLimiter:
    """Simple in-memory sliding-window limiter keyed by sender address."""

    def __init__(self, *, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = Lock()
        self._history: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            history = self._history.setdefault(key, deque())
            while history and history[0] < cutoff:
                history.popleft()
            if len(history) >= self.limit:
                return False
            history.append(now)
            return True


def _parse_basic_auth(authorization: str) -> tuple[str | None, str | None]:
    if not authorization or not authorization.startswith("Basic "):
        return None, None
    token = authorization.split(" ", 1)[1].strip()
    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
    except Exception:
        return None, None
    if ":" not in decoded:
        return None, None
    user, password = decoded.split(":", maxsplit=1)
    return user, password


def _verify_password(cleartext_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False
    stored_password = stored_password.strip()
    if stored_password.startswith(PASSWORD_PREFIX):
        stored_password = stored_password[len(PASSWORD_PREFIX) :]
    if not stored_password:
        return False
    try:
        computed = crypt_r.crypt(cleartext_password, stored_password)
    except Exception:
        return False
    return computed == stored_password


def _authenticate_local_user(
    config: Config, authorization: str
) -> tuple[str | None, str | None]:
    user, password = _parse_basic_auth(authorization)
    user = (user or "").strip()
    password = password or ""

    if not user or not password:
        return None, "missing or invalid basic auth credentials"
    if not user.endswith(f"@{config.mail_domain}"):
        return None, f"user must end with @{config.mail_domain}"

    try:
        cfg_user = config.get_user(user)
    except ValueError:
        return None, "invalid user format"

    userdata = cfg_user.get_userdb_dict()
    if not userdata:
        return None, "invalid credentials"
    stored_password = str(userdata.get("password", ""))
    if not _verify_password(password, stored_password):
        return None, "invalid credentials"
    return user, None


def _local_account_exists(config: Config, addr: str) -> bool:
    try:
        user = config.get_user(addr)
    except ValueError:
        return False
    return bool(user.get_userdb_dict())


class EventsHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr: tuple[str, int], config: Config):
        super().__init__(addr, EventsHandler)
        self.config = config
        self.bus = EventBus()
        self.rate_limiter = SlidingWindowRateLimiter(limit=120, window_seconds=60)


class EventsHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        logging.info("chatmail-events %s - %s", self.address_string(), fmt % args)

    @property
    def server_typed(self) -> EventsHTTPServer:
        return self.server  # type: ignore[return-value]

    def _send_json(self, status_code: int, payload: dict, *, close: bool = True):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if close:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def _send_auth_required(self, msg: str):
        body = json.dumps({"error": msg}).encode("utf-8")
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="chatmail-events"')
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def _authenticate(self) -> str | None:
        user, err = _authenticate_local_user(
            self.server_typed.config, self.headers.get("Authorization", "")
        )
        if not user:
            self._send_auth_required(err or "unauthorized")
            return None
        return user

    def _read_json_body(self) -> tuple[dict | None, tuple[int, str] | None]:
        raw_len = self.headers.get("Content-Length", "0").strip()
        try:
            content_length = int(raw_len)
        except ValueError:
            return None, (400, "invalid content-length")
        if content_length <= 0:
            return None, (400, "request body is required")
        if content_length > MAX_BODY_LEN:
            return None, (413, "request body too large")

        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return None, (400, "invalid json payload")
        if not isinstance(payload, dict):
            return None, (400, "json payload must be an object")
        return payload, None

    def _write_sse(self, event_name: str, payload: dict):
        data = json.dumps(payload, separators=(",", ":"))
        self.wfile.write(f"event: {event_name}\n".encode("utf-8"))
        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
        self.wfile.flush()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path != STREAM_PATH:
            self._send_json(404, {"error": "not found"})
            return

        addr = self._authenticate()
        if not addr:
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        client_id, q = self.server_typed.bus.register(addr)
        try:
            self._write_sse("ready", {"status": "ok"})
            while True:
                try:
                    event = q.get(timeout=20)
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                self._write_sse(str(event.get("event", "event")), event)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        finally:
            self.server_typed.bus.unregister(addr, client_id)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path != SEND_PATH:
            self._send_json(404, {"error": "not found"})
            return

        sender = self._authenticate()
        if not sender:
            return

        if not self.server_typed.rate_limiter.allow(sender):
            self._send_json(429, {"error": "rate limit exceeded"})
            return

        payload, err = self._read_json_body()
        if err:
            code, msg = err
            self._send_json(code, {"error": msg})
            return
        assert payload is not None

        to_addr = str(payload.get("to", "")).strip()
        event_name = str(payload.get("event", "")).strip()
        event_payload = payload.get("payload", {})

        if not to_addr:
            self._send_json(400, {"error": "to is required"})
            return
        if not to_addr.endswith(f"@{self.server_typed.config.mail_domain}"):
            self._send_json(
                400,
                {"error": f"to must end with @{self.server_typed.config.mail_domain}"},
            )
            return
        if not EVENT_RE.match(event_name):
            self._send_json(
                400,
                {"error": "event must match ^[a-z0-9_-]{1,32}$"},
            )
            return
        if not isinstance(event_payload, dict):
            self._send_json(400, {"error": "payload must be an object"})
            return
        if not _local_account_exists(self.server_typed.config, to_addr):
            self._send_json(404, {"error": "target account not found"})
            return

        event = {
            "event": event_name,
            "from": sender,
            "to": to_addr,
            "payload": event_payload,
            "ts": int(time.time()),
        }
        delivered = self.server_typed.bus.publish(to_addr, event)
        self._send_json(
            202,
            {"status": "accepted", "event": event_name, "delivered_to_connections": delivered},
        )


def _parse_listen(s: str) -> tuple[str, int]:
    if ":" not in s:
        raise ValueError("listen address must be HOST:PORT")
    host, port = s.rsplit(":", maxsplit=1)
    host = host.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not host:
        raise ValueError("listen host can not be empty")
    return host, int(port)


def main():
    listen, config_path = sys.argv[1:]
    host, port = _parse_listen(listen)
    config = read_config(config_path)
    server = EventsHTTPServer((host, port), config)
    server.serve_forever()


if __name__ == "__main__":
    main()

