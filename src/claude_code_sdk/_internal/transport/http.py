import httpx
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any, AsyncContextManager

from claude_code_sdk._internal.transport import Transport
from claude_code_sdk._errors import NetworkError


class HttpTransport(Transport):
    """HTTP transport for Claude communication."""

    def __init__(self, *, url: str):
        self._url = url
        self._client: httpx.AsyncClient | None = None
        self._response_context: AsyncContextManager[httpx.Response] | None = None
        self._response_iterator: AsyncIterator[dict[str, Any]] | None = None

    async def connect(self) -> None:
        """Initialize connection."""
        if self.is_connected():
            return

        # Using a long timeout for potentially long-running tools
        timeout = httpx.Timeout(300.0, connect=60.0)
        self._client = httpx.AsyncClient(
            http2=True, timeout=timeout, base_url=self._url
        )

    async def disconnect(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send_request(
        self, messages: list[dict[str, Any]], options: dict[str, Any]
    ) -> None:
        """Send request to Claude."""
        if not self.is_connected() or self._client is None:
            raise NetworkError("Transport is not connected.")

        if self._response_context is not None:
            raise NetworkError("Another request is already in progress.")

        tool_name = options.get("tool_name")
        if not tool_name:
            raise ValueError("tool_name must be provided in options")

        request = {
            "jsonrpc": "2.0",
            "method": "invoke",
            "params": {"tool_name": tool_name, "messages": messages},
            "id": str(uuid.uuid4()),
        }

        try:
            self._response_context = self._client.stream(
                "POST", "/invoke", json=request
            )
        except httpx.RequestError as e:
            raise NetworkError(f"HTTP request failed: {e}") from e

    async def _message_iterator(self) -> AsyncIterator[dict[str, Any]]:
        if self._response_context is None:
            # This should not happen if used correctly
            return

        try:
            async with self._response_context as response:
                response.raise_for_status()

                buffer = ""
                decoder = json.JSONDecoder()
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while buffer:
                        try:
                            obj, index = decoder.raw_decode(buffer)
                            yield obj
                            buffer = buffer[index:].lstrip()
                        except json.JSONDecodeError:
                            # Incomplete JSON object, wait for more data
                            break
        except httpx.HTTPStatusError as e:
            raise NetworkError(
                f"HTTP Error: {e.response.status_code} {e.response.reason_phrase}"
            ) from e
        except httpx.RequestError as e:
            raise NetworkError(f"HTTP request failed: {e}") from e
        finally:
            self._response_context = None
            self._response_iterator = None

    def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """Receive messages from Claude."""
        if self._response_context is None:
            raise NetworkError("No request has been sent. Call send_request first.")

        if self._response_iterator is None:
            self._response_iterator = self._message_iterator()

        return self._response_iterator

    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._client is not None and not self._client.is_closed
