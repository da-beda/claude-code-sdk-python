import json
import uuid

import httpx
import pytest

from claude_code_sdk._errors import NetworkError
from claude_code_sdk._internal.transport.http import HttpTransport

BASE_URL = "http://mock-server"


@pytest.fixture
def mock_transport_handler():
    """Request handler for the mock transport."""

    def handler(request: httpx.Request):
        if request.url.path == "/invoke":
            # Simulate a streaming response with concatenated JSON
            stream_content = [
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Hello"}]},
                },
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": " World"}]},
                },
            ]
            response_bytes = "".join(
                json.dumps(item) for item in stream_content
            ).encode("utf-8")
            return httpx.Response(200, content=response_bytes)

        if request.url.path == "/error":
            return httpx.Response(500, text="Internal Server Error")

        if request.url.path == "/connect_error":
            raise httpx.ConnectError("Connection failed", request=request)

        return httpx.Response(404, text="Not Found")

    return handler


@pytest.fixture
def mock_transport(mock_transport_handler) -> httpx.MockTransport:
    """Fixture for the mock transport."""
    return httpx.MockTransport(mock_transport_handler)


@pytest.fixture
def http_transport(mock_transport: httpx.MockTransport) -> HttpTransport:
    """Fixture for HttpTransport configured with a mock client."""
    transport = HttpTransport(url=BASE_URL)
    transport._client = httpx.AsyncClient(transport=mock_transport, base_url=BASE_URL)
    return transport


@pytest.mark.asyncio
async def test_http_transport_connect_disconnect():
    """Test that the transport can connect and disconnect."""
    transport = HttpTransport(url=BASE_URL)
    assert not transport.is_connected()
    await transport.connect()
    assert transport.is_connected()
    assert transport._client is not None
    await transport.disconnect()
    assert transport._client is None
    assert not transport.is_connected()


@pytest.mark.asyncio
async def test_http_transport_successful_stream(http_transport: HttpTransport):
    """Test a successful request and streaming response."""
    await http_transport.send_request(
        messages=[{"role": "user", "content": "Hello"}],
        options={"tool_name": "test_tool"},
    )

    messages = [msg async for msg in http_transport.receive_messages()]

    assert len(messages) == 2
    assert messages[0]["type"] == "assistant"
    assert messages[0]["message"]["content"][0]["text"] == "Hello"
    assert messages[1]["message"]["content"][0]["text"] == " World"


@pytest.mark.asyncio
async def test_http_transport_http_error(
    mock_transport: httpx.MockTransport, http_transport: HttpTransport
):
    """Test that an HTTP error status code raises a NetworkError."""

    async def handler_with_error(request: httpx.Request):
        return httpx.Response(500, text="Internal Server Error")

    mock_transport.handler = handler_with_error

    with pytest.raises(NetworkError, match="HTTP Error: 500 Internal Server Error"):
        await http_transport.send_request(messages=[], options={"tool_name": "test"})
        async for _ in http_transport.receive_messages():
            pass


@pytest.mark.asyncio
async def test_http_transport_connection_error(
    mock_transport: httpx.MockTransport,
):
    """Test that a connection error during the request raises a NetworkError."""

    async def handler_with_connect_error(request: httpx.Request):
        raise httpx.ConnectError("Connection failed", request=request)

    mock_transport.handler = handler_with_connect_error
    transport = HttpTransport(url=BASE_URL)
    transport._client = httpx.AsyncClient(transport=mock_transport, base_url=BASE_URL)

    with pytest.raises(NetworkError, match="HTTP request failed"):
        # The error is raised when the stream is consumed
        await transport.send_request(messages=[], options={"tool_name": "test"})
        async for _ in transport.receive_messages():
            pass


@pytest.mark.asyncio
async def test_http_transport_concurrent_request_error(http_transport: HttpTransport):
    """Test that a second request before the first is finished raises an error."""
    await http_transport.send_request(messages=[], options={"tool_name": "test1"})

    with pytest.raises(NetworkError, match="Another request is already in progress"):
        await http_transport.send_request(messages=[], options={"tool_name": "test2"})


@pytest.mark.asyncio
async def test_receive_before_send_raises_error(http_transport: HttpTransport):
    """Test that calling receive_messages before send_request raises an error."""
    with pytest.raises(NetworkError, match="No request has been sent"):
        async for _ in http_transport.receive_messages():
            pass
