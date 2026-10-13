"""WebSocket DDP client for TrueNAS."""
import asyncio
import json
import logging
import ssl
from typing import Any

import websockets

logger = logging.getLogger(__name__)


class TrueNASClient:
    """Persistent WebSocket connection to TrueNAS DDP API."""

    def __init__(self, url: str, api_key: str, verify_ssl: bool = False, timeout: float = 30.0):
        # Normalize URL: accept https:// or wss:// or bare hostname
        if url.startswith("https://"):
            url = "wss://" + url[8:]
        elif url.startswith("http://"):
            url = "ws://" + url[7:]
        if not url.startswith(("ws://", "wss://")):
            url = "wss://" + url
        # Ensure /websocket path
        if not url.endswith("/websocket"):
            url = url.rstrip("/") + "/websocket"

        self._url = url
        self._api_key = api_key
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._ws = None
        self._msg_id = 0
        self._handlers: dict[str, asyncio.Future] = {}
        self._listen_task: asyncio.Task | None = None
        self._connected = False

    async def connect(self):
        """Connect, handshake, and authenticate."""
        ssl_ctx = None
        if self._url.startswith("wss://"):
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if not self._verify_ssl:
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

        self._ws = await websockets.connect(self._url, ssl=ssl_ctx)
        self._listen_task = asyncio.create_task(self._listener())

        # DDP handshake
        await self._ws.send(json.dumps({"msg": "connect", "version": "1", "support": ["1"]}))
        # Wait for connected message (handled by listener setting _connected)
        for _ in range(50):  # 5s max
            if self._connected:
                break
            await asyncio.sleep(0.1)
        if not self._connected:
            raise ConnectionError("DDP handshake failed")

        # Authenticate
        result = await self.call("auth.login_with_api_key", [self._api_key])
        if result is not True:
            raise ConnectionError("Authentication failed")
        logger.info("Connected and authenticated to %s", self._url)

    async def call(self, method: str, params: list | None = None) -> Any:
        """Call a TrueNAS API method and return the result."""
        if not self._ws or not self._connected:
            await self.connect()

        self._msg_id += 1
        msg_id = str(self._msg_id)
        future = asyncio.get_event_loop().create_future()
        self._handlers[msg_id] = future

        await self._ws.send(json.dumps({
            "id": msg_id,
            "msg": "method",
            "method": method,
            "params": params or [],
        }))

        try:
            msg = await asyncio.wait_for(future, timeout=self._timeout)
        except asyncio.TimeoutError:
            self._handlers.pop(msg_id, None)
            raise TimeoutError(f"Call to {method} timed out after {self._timeout}s")

        if "error" in msg:
            err = msg["error"]
            raise RuntimeError(f"API error in {method}: {err.get('reason', err)}")

        return msg.get("result")

    async def call_first(self, candidates: list[tuple[str, list | None]]) -> Any:
        """Call the first (method, params) pair this TrueNAS version implements.

        Methods get renamed between releases; list the newest name first. Only a
        missing method ([ENOMETHOD]) falls through to the next candidate.
        """
        for index, (method, params) in enumerate(candidates):
            try:
                return await self.call(method, params)
            except RuntimeError as exc:
                if "[ENOMETHOD]" not in str(exc) or index == len(candidates) - 1:
                    raise
                logger.debug("%s not available, trying %s", method, candidates[index + 1][0])

    async def _listener(self):
        """Background task that routes incoming messages."""
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                if msg.get("msg") == "connected":
                    self._connected = True
                elif msg.get("msg") == "result" and "id" in msg:
                    future = self._handlers.pop(msg["id"], None)
                    if future and not future.done():
                        future.set_result(msg)
                # Ignore other messages (pings, notifications)
        except websockets.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self._connected = False
            self._ws = None

    async def close(self):
        """Close the connection."""
        if self._listen_task:
            self._listen_task.cancel()
            self._listen_task = None
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._connected = False
