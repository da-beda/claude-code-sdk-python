"""Claude SDK Client for interacting with Claude Code."""

import os
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

import anyio
from anyio.abc import TaskGroup

from ._errors import CLIConnectionError
from .types import (
    ClaudeCodeOptions,
    ElicitationRequestHandler,
    ElicitationRequestMessage,
    Message,
    NotificationHandler,
    NotificationMessage,
    ResourceRequestHandler,
    ResourceRequestMessage,
    ResultMessage,
    ToolsChangedHandler,
    ToolsChangedMessage,
)


class ClaudeSDKClient:
    """
    Client for bidirectional, interactive conversations with Claude Code.

    This client provides full control over the conversation flow with support
    for streaming, interrupts, and dynamic message sending. For simple one-shot
    queries, consider using the query() function instead.

    Key features:
    - **Bidirectional**: Send and receive messages at any time, with support
      for server-initiated events like notifications and elicitation requests.
    - **Stateful**: Maintains conversation context across messages
    - **Interactive**: Send follow-ups based on responses
    - **Control flow**: Support for interrupts and session management

    When to use ClaudeSDKClient:
    - Building chat interfaces or conversational UIs
    - Interactive debugging or exploration sessions
    - Multi-turn conversations with context
    - When you need to react to Claude's responses and server events
    - Real-time applications with user input
    - When you need interrupt capabilities

    When to use query() instead:
    - Simple one-off questions
    - Batch processing of prompts
    - Fire-and-forget automation scripts
    - When all inputs are known upfront
    - Stateless operations

    Example - Interactive conversation with event handlers:
        ```python
        client = ClaudeSDKClient()

        # Define handlers for server-initiated events
        async def handle_notification(msg: NotificationMessage):
            print(f"Server notification: {msg.message}")

        async def handle_elicitation(req: ElicitationRequestMessage) -> str:
            response = input(f"Server asks: {req.prompt} ")
            return response

        # Register handlers
        client.on_notification(handle_notification)
        client.on_elicitation_request(handle_elicitation)

        async with client:
            await client.query("Start a process that will send notifications.")
            # The client will automatically handle incoming events in the background
            # while you can continue to interact with it.
            await client.query("What is 2+2?")
            async for message in client.receive_response():
                print(message)
        ```
    """

    def __init__(
        self,
        options: ClaudeCodeOptions | None = None,
        *,
        on_notification: NotificationHandler | None = None,
        on_elicitation_request: ElicitationRequestHandler | None = None,
        on_tools_changed: ToolsChangedHandler | None = None,
        on_resource_request: ResourceRequestHandler | None = None,
    ):
        """Initialize Claude SDK client."""
        if options is None:
            options = ClaudeCodeOptions()
        self.options = options
        self._transport: Any | None = None
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-py-client"

        # Event handlers
        self._on_notification_handler: NotificationHandler | None = None
        self._on_elicitation_request_handler: ElicitationRequestHandler | None = None
        self._on_tools_changed_handler: ToolsChangedHandler | None = None
        self._on_resource_request_handler: ResourceRequestHandler | None = None

        # Background processing
        self._send_stream: anyio.abc.ObjectSendStream[Message | None] | None = None
        self._receive_stream: anyio.abc.ObjectReceiveStream[Message | None] | None = None
        self._tg: TaskGroup | None = None

        if on_notification:
            self.on_notification(on_notification)
        if on_elicitation_request:
            self.on_elicitation_request(on_elicitation_request)
        if on_tools_changed:
            self.on_tools_changed(on_tools_changed)
        if on_resource_request:
            self.on_resource_request(on_resource_request)

    def on_notification(self, handler: NotificationHandler) -> None:
        """Register a handler for notification events."""
        self._on_notification_handler = handler

    def on_elicitation_request(self, handler: ElicitationRequestHandler) -> None:
        """Register a handler for elicitation requests from the server."""
        self._on_elicitation_request_handler = handler

    def on_tools_changed(self, handler: ToolsChangedHandler) -> None:
        """Register a handler for tools_changed events."""
        self._on_tools_changed_handler = handler

    def on_resource_request(self, handler: ResourceRequestHandler) -> None:
        """Register a handler for resource requests from the server."""
        self._on_resource_request_handler = handler

    async def _message_pump(self) -> None:
        if not self._transport or not self._send_stream:
            return

        from ._internal.message_parser import parse_message

        try:
            async with self._send_stream:
                async for data in self._transport.receive_messages():
                    message = parse_message(data)

                    if isinstance(message, NotificationMessage):
                        if self._on_notification_handler:
                            await self._on_notification_handler(message)
                    elif isinstance(message, ElicitationRequestMessage):
                        if self._on_elicitation_request_handler:
                            response = await self._on_elicitation_request_handler(
                                message
                            )
                            await self._transport.send_elicitation_response(
                                message.id, response
                            )
                    elif isinstance(message, ToolsChangedMessage):
                        if self._on_tools_changed_handler:
                            await self._on_tools_changed_handler(message)
                    elif isinstance(message, ResourceRequestMessage):
                        if self._on_resource_request_handler:
                            content = await self._on_resource_request_handler(message)
                            await self._transport.send_elicitation_response(
                                message.id, content
                            )
                    else:
                        await self._send_stream.send(message)
        except (CLIConnectionError, anyio.EndOfStream):
            pass

    async def connect(
        self, prompt: str | AsyncIterable[dict[str, Any]] | None = None
    ) -> None:
        """Connect to Claude and start background message processing."""
        from ._internal.transport.subprocess_cli import SubprocessCLITransport

        async def _empty_stream() -> AsyncIterator[dict[str, Any]]:
            return
            yield {}  # type: ignore[unreachable]

        self._transport = SubprocessCLITransport(
            prompt=_empty_stream() if prompt is None else prompt,
            options=self.options,
        )
        await self._transport.connect()

        send_stream, receive_stream = anyio.create_memory_object_stream(100)
        self._send_stream = send_stream
        self._receive_stream = receive_stream
        if self._tg:
            self._tg.start_soon(self._message_pump)

    async def receive_messages(self) -> AsyncIterator[Message]:
        """
        Receive messages from Claude, handling server-initiated events automatically.

        This async iterator yields standard messages (User, Assistant, System, Result)
        while transparently handling events like notifications and elicitation
        requests in the background via their registered handlers.
        """
        if not self._transport or not self._receive_stream:
            raise CLIConnectionError("Not connected. Call connect() first.")

        async for message in self._receive_stream:
            yield message

    async def query(
        self, prompt: str | AsyncIterable[dict[str, Any]], session_id: str = "default"
    ) -> None:
        """
        Send a new request in streaming mode.
        """
        if not self._transport:
            raise CLIConnectionError("Not connected. Call connect() first.")

        if isinstance(prompt, str):
            message = {
                "type": "user",
                "message": {"role": "user", "content": prompt},
                "parent_tool_use_id": None,
                "session_id": session_id,
            }
            await self._transport.send_request([message], {"session_id": session_id})
        else:
            messages = []
            async for msg in prompt:
                if "session_id" not in msg:
                    msg["session_id"] = session_id
                messages.append(msg)

            if messages:
                await self._transport.send_request(messages, {"session_id": session_id})

    async def interrupt(self) -> None:
        """Send interrupt signal (only works with streaming mode)."""
        if not self._transport:
            raise CLIConnectionError("Not connected. Call connect() first.")
        await self._transport.interrupt()

    async def receive_response(self) -> AsyncIterator[Message]:
        """
        Receive messages from Claude until a ResultMessage is received.
        """
        async for message in self.receive_messages():
            yield message
            if isinstance(message, ResultMessage):
                return

    async def disconnect(self) -> None:
        """Disconnect from Claude."""
        if self._transport:
            await self._transport.disconnect()
            self._transport = None

    async def __aenter__(self) -> "ClaudeSDKClient":
        """Enter async context - automatically connects and starts background processing."""
        self._tg = anyio.create_task_group()
        await self._tg.__aenter__()
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit async context - always disconnects."""
        await self.disconnect()
        if self._tg:
            await self._tg.__aexit__(exc_type, exc_val, exc_tb)
            self._tg = None
        return False
