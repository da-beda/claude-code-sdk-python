"""Tests for event handlers in ClaudeSDKClient."""

from unittest.mock import AsyncMock, patch

import anyio

from claude_code_sdk import ClaudeSDKClient, NotificationMessage, ElicitationRequestMessage, ToolsChangedMessage


class TestEventHandlers:
    """Validate that client event handlers are invoked."""

    def test_notification_handler_called(self):
        async def _test():
            with patch(
                "claude_code_sdk._internal.transport.subprocess_cli.SubprocessCLITransport"
            ) as mock_transport_class:
                mock_transport = AsyncMock()
                mock_transport_class.return_value = mock_transport

                async def mock_receive():
                    yield {"type": "notification", "level": "info", "message": "hello"}

                mock_transport.receive_messages = mock_receive
                mock_transport.connect = AsyncMock()
                mock_transport.disconnect = AsyncMock()

                events: list[NotificationMessage] = []

                async with ClaudeSDKClient() as client:
                    client.set_notification_handler(lambda m: events.append(m))
                    msgs = [m async for m in client.receive_messages()]

                assert len(events) == 1
                assert isinstance(events[0], NotificationMessage)
                assert events[0].message == "hello"
                assert isinstance(msgs[0], NotificationMessage)

        anyio.run(_test)

    def test_elicitation_handler_called(self):
        async def _test():
            with patch(
                "claude_code_sdk._internal.transport.subprocess_cli.SubprocessCLITransport"
            ) as mock_transport_class:
                mock_transport = AsyncMock()
                mock_transport_class.return_value = mock_transport

                async def mock_receive():
                    yield {"type": "elicitation_request", "id": "1", "prompt": "Why?"}

                mock_transport.receive_messages = mock_receive
                mock_transport.connect = AsyncMock()
                mock_transport.disconnect = AsyncMock()

                events: list[ElicitationRequestMessage] = []

                async with ClaudeSDKClient() as client:
                    client.set_elicitation_request_handler(lambda m: events.append(m))
                    _ = [m async for m in client.receive_messages()]

                assert len(events) == 1
                assert isinstance(events[0], ElicitationRequestMessage)
                assert events[0].prompt == "Why?"

        anyio.run(_test)

    def test_tools_changed_handler_called(self):
        async def _test():
            with patch(
                "claude_code_sdk._internal.transport.subprocess_cli.SubprocessCLITransport"
            ) as mock_transport_class:
                mock_transport = AsyncMock()
                mock_transport_class.return_value = mock_transport

                async def mock_receive():
                    yield {"type": "tools_changed", "tools": ["A"]}

                mock_transport.receive_messages = mock_receive
                mock_transport.connect = AsyncMock()
                mock_transport.disconnect = AsyncMock()

                events: list[ToolsChangedMessage] = []

                async with ClaudeSDKClient() as client:
                    client.set_tools_changed_handler(lambda m: events.append(m))
                    _ = [m async for m in client.receive_messages()]

                assert len(events) == 1
                assert isinstance(events[0], ToolsChangedMessage)
                assert events[0].tools == ["A"]

        anyio.run(_test)
