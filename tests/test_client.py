"""Tests for TrueNAS WebSocket client."""
import os
import pytest
from truenas_ws_mcp.client import TrueNASClient

TRUENAS_URL = os.environ.get("TRUENAS_URL", "")
TRUENAS_API_KEY = os.environ.get("TRUENAS_API_KEY", "")


def test_url_normalization_https():
    client = TrueNASClient("https://truenas.local", "fake-key")
    assert client._url == "wss://truenas.local/websocket"


def test_url_normalization_bare():
    client = TrueNASClient("truenas.local", "fake-key")
    assert client._url == "wss://truenas.local/websocket"


def test_url_normalization_already_wss():
    client = TrueNASClient("wss://truenas.local/websocket", "fake-key")
    assert client._url == "wss://truenas.local/websocket"


def test_url_normalization_http():
    client = TrueNASClient("http://truenas.local", "fake-key")
    assert client._url == "ws://truenas.local/websocket"


def _fake_call(results):
    """Stand-in for TrueNASClient.call: raise or return per method name."""
    calls = []

    async def call(method, params=None):
        calls.append(method)
        outcome = results[method]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return call, calls


@pytest.mark.asyncio
async def test_call_first_falls_back_on_enomethod():
    client = TrueNASClient("truenas.local", "fake-key")
    client.call, calls = _fake_call({
        "new.method": RuntimeError("API error in new.method: [ENOMETHOD] Method 'method' not found"),
        "old.method": "ok",
    })
    assert await client.call_first([("new.method", []), ("old.method", [])]) == "ok"
    assert calls == ["new.method", "old.method"]


@pytest.mark.asyncio
async def test_call_first_does_not_swallow_other_errors():
    client = TrueNASClient("truenas.local", "fake-key")
    client.call, calls = _fake_call({
        "new.method": RuntimeError("API error in new.method: [EINVAL] bad filter"),
        "old.method": "ok",
    })
    with pytest.raises(RuntimeError, match="EINVAL"):
        await client.call_first([("new.method", []), ("old.method", [])])
    assert calls == ["new.method"]


@pytest.mark.asyncio
async def test_call_first_raises_last_enomethod():
    client = TrueNASClient("truenas.local", "fake-key")
    client.call, _ = _fake_call({
        "new.method": RuntimeError("API error in new.method: [ENOMETHOD] missing"),
        "old.method": RuntimeError("API error in old.method: [ENOMETHOD] missing"),
    })
    with pytest.raises(RuntimeError, match="old.method"):
        await client.call_first([("new.method", []), ("old.method", [])])


@pytest.mark.skipif(not TRUENAS_URL or not TRUENAS_API_KEY, reason="TRUENAS_URL/TRUENAS_API_KEY not set")
@pytest.mark.asyncio
async def test_connect_and_system_info():
    client = TrueNASClient(TRUENAS_URL, TRUENAS_API_KEY, verify_ssl=False)
    await client.connect()
    info = await client.call("system.info", [])
    assert "version" in info
    assert "uptime" in info
    await client.close()
