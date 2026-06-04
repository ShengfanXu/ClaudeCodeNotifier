# tests/test_http_server.py
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from src.http_server import create_app, NotifyRequest


class TestNotifyRequest:
    """Tests for request parsing."""

    def test_notify_request_from_dict(self):
        req = NotifyRequest(reason="stop_hook", message="Test message")
        assert req.reason == "stop_hook"
        assert req.message == "Test message"

    def test_notify_request_defaults(self):
        req = NotifyRequest()
        assert req.reason == ""
        assert req.message == ""


class TestCreateApp:
    """Tests for the aiohttp app and routes."""

    @pytest.mark.asyncio
    async def test_notify_endpoint_returns_200(self):
        received = []

        async def handler(req: NotifyRequest):
            received.append(req)
            return web.json_response({"status": "ok"})

        app = create_app(on_notify=handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/notify", json={"reason": "stop_hook"})
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "ok"
            assert len(received) == 1
            assert received[0].reason == "stop_hook"

    @pytest.mark.asyncio
    async def test_notify_endpoint_invalid_json_returns_400(self):
        app = create_app(on_notify=lambda req: web.json_response({"status": "ok"}))
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/notify", data="not json")
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        app = create_app(on_notify=lambda req: web.json_response({"status": "ok"}))
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_notify_with_empty_body(self):
        async def handler(req: NotifyRequest) -> web.Response:
            return web.json_response({"status": "ok"})

        app = create_app(on_notify=handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/notify", json={})
            assert resp.status == 200
