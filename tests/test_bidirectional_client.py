import anyio
import pytest
from unittest.mock import AsyncMock, MagicMock

from claude_code_sdk import (
    ClaudeSDKClient,
    ElicitationRequestMessage,
    NotificationMessage,
    ResourceRequestMessage,
    ToolsChangedMessage,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def mock_transport():
    """Fixture to create a mock transport."""
    transport = MagicMock()
    transport.connect = AsyncMock()
    transport.disconnect = AsyncMock()
    transport.send_request = AsyncMock()
    transport.send_elicitation_response = AsyncMock()
    transport.interrupt = AsyncMock()

    # This will be our way to inject messages from the "server"
    transport.receive_messages = lambda: None # Placeholder

    return transport


@pytest.fixture
def client(monkeypatch, mock_transport):
    """Fixture to create a ClaudeSDKClient with a mock transport."""
    monkeypatch.setattr(
        "claude_code_sdk._internal.transport.subprocess_cli.SubprocessCLITransport",
        MagicMock(return_value=mock_transport),
    )
    return ClaudeSDKClient()


async def test_notification_handler(client: ClaudeSDKClient, mock_transport):
    """Test that the notification handler is called for notification events."""
    notification_handler = AsyncMock()
    client.on_notification(notification_handler)

    # Simulate receiving a notification message from the transport
    notification_event = {
        "type": "notification",
        "method": "log/info",
        "params": {"message": "This is a test notification."},
    }

    async def message_stream():
        yield notification_event
        # Yield a result message to terminate the receive_response loop
        yield {"type": "result", "subtype": "success", "session_id": "123", "num_turns": 1, "duration_ms": 1, "duration_api_ms": 1, "is_error": False}

    mock_transport.receive_messages = message_stream

    async with client:
        # We need to consume messages to drive the message pump
        async for _ in client.receive_response():
            pass

    notification_handler.assert_awaited_once()
    call_args = notification_handler.call_args[0][0]
    assert isinstance(call_args, NotificationMessage)
    assert call_args.method == "log/info"
    assert call_args.params["message"] == "This is a test notification."


async def test_elicitation_request_handler(client: ClaudeSDKClient, mock_transport):
    """Test the full round-trip for an elicitation request."""
    async def elicitation_handler(req: ElicitationRequestMessage) -> str:
        assert req.id == "elicit-123"
        assert req.prompt == "What is your name?"
        return "Jules"

    client.on_elicitation_request(elicitation_handler)

    elicitation_event = {
        "type": "elicitation_request",
        "id": "elicit-123",
        "prompt": "What is your name?",
    }

    async def message_stream():
        yield elicitation_event
        yield {"type": "result", "subtype": "success", "session_id": "123", "num_turns": 1, "duration_ms": 1, "duration_api_ms": 1, "is_error": False}

    mock_transport.receive_messages = message_stream

    async with client:
        async for _ in client.receive_response():
            pass

    # Check that the response was sent back to the transport
    mock_transport.send_elicitation_response.assert_awaited_once_with(
        "elicit-123", "Jules"
    )

async def test_tools_changed_handler(client: ClaudeSDKClient, mock_transport):
    """Test that the tools_changed handler is called."""
    handler = AsyncMock()
    client.on_tools_changed(handler)

    event = {
        "type": "tools_changed",
        "added_tools": ["new_tool"],
        "removed_tools": ["old_tool"],
    }

    async def message_stream():
        yield event
        yield {"type": "result", "subtype": "success", "session_id": "123", "num_turns": 1, "duration_ms": 1, "duration_api_ms": 1, "is_error": False}

    mock_transport.receive_messages = message_stream

    async with client:
        async for _ in client.receive_response():
            pass

    handler.assert_awaited_once()
    call_args = handler.call_args[0][0]
    assert isinstance(call_args, ToolsChangedMessage)
    assert call_args.added_tools == ["new_tool"]
    assert call_args.removed_tools == ["old_tool"]


async def test_resource_request_handler(client: ClaudeSDKClient, mock_transport):
    """Test the full round-trip for a resource request."""
    async def resource_handler(req: ResourceRequestMessage) -> str:
        assert req.id == "resource-456"
        assert req.name == "path/to/file.txt"
        return "File content"

    client.on_resource_request(resource_handler)

    event = {
        "type": "resource_request",
        "id": "resource-456",
        "name": "path/to/file.txt",
    }

    async def message_stream():
        yield event
        yield {"type": "result", "subtype": "success", "session_id": "123", "num_turns": 1, "duration_ms": 1, "duration_api_ms": 1, "is_error": False}

    mock_transport.receive_messages = message_stream

    async with client:
        async for _ in client.receive_response():
            pass

    mock_transport.send_elicitation_response.assert_awaited_once_with(
        "resource-456", "File content"
    )


def test_constructor_handlers():
    """Test that handlers can be passed via the constructor."""
    handler = AsyncMock()
    client = ClaudeSDKClient(on_notification=handler)
    assert client._on_notification_handler is handler
