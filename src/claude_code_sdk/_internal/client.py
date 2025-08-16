"""Internal client implementation."""

from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

from .._errors import ToolExecutionError
from ..types import ClaudeCodeOptions, Message
from .message_parser import parse_message
from .transport import Transport
from .transport.http import HttpTransport
from .transport.subprocess_cli import SubprocessCLITransport


class InternalClient:
    """Internal client implementation."""

    def __init__(self) -> None:
        """Initialize the internal client."""

    async def process_query(
        self, prompt: str | AsyncIterable[dict[str, Any]], options: ClaudeCodeOptions
    ) -> AsyncIterator[Message]:
        """Process a query through transport."""

        transport: Transport
        transport_config = options.transport
        if transport_config and transport_config.get("type") == "http":
            url = transport_config.get("url")
            if not url:
                raise ValueError("HTTP transport config missing 'url'")
            transport = HttpTransport(url=url)
        else:
            transport = SubprocessCLITransport(
                prompt=prompt, options=options, close_stdin_after_prompt=True
            )

        try:
            await transport.connect()

            if isinstance(transport, HttpTransport):
                messages: list[dict[str, Any]]
                if isinstance(prompt, str):
                    messages = [
                        {"type": "user", "message": {"role": "user", "content": prompt}}
                    ]
                else:
                    messages = [p async for p in prompt]
                await transport.send_request(messages, {})

            async for data in transport.receive_messages():
                if "error" in data and data.get("error"):
                    error_data = data["error"]
                    hint = error_data.get("data", {}).get("hint")
                    raise ToolExecutionError(
                        message=error_data.get("message", "Unknown error"),
                        code=error_data.get("code", -1),
                        hint=hint,
                    )
                yield parse_message(data)

        finally:
            await transport.disconnect()
