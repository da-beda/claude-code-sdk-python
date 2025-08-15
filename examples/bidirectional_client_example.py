"""
This example demonstrates the bidirectional capabilities of the ClaudeSDKClient,
showing how to handle server-initiated events like notifications and elicitation
requests.

To make this example runnable without a live server that sends these events,
it uses a mocked transport layer that simulates them.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import anyio

from claude_code_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ElicitationRequestMessage,
    NotificationMessage,
    ResultMessage,
    TextBlock,
)


# --- Handler Definitions ---
# These are the functions that will be called when the server sends an event.
async def handle_notification(notification: NotificationMessage):
    """Handles incoming notifications from the server."""
    print(
        f"\n[SERVER NOTIFICATION] Method: {notification.method}, "
        f"Params: {notification.params}"
    )


async def handle_elicitation(request: ElicitationRequestMessage) -> str:
    """Handles an elicitation request from the server and returns a response."""
    print(f"\n[SERVER ELICITATION] Server asks: {request.prompt}")
    response = input("Your response: ")
    return response


# --- Mock Transport Setup ---
# This class simulates the behavior of the real transport layer for demonstration.
class MockTransport:
    def __init__(self):
        self._send_stream, self._receive_stream = anyio.create_memory_object_stream()
        self.send_elicitation_response = AsyncMock()

    async def connect(self):
        print("[MockTransport] Connected.")

    async def disconnect(self):
        print("[MockTransport] Disconnected.")

    async def send_request(self, messages, options):
        print(f"[MockTransport] Received query: {messages[0]['message']['content']}")
        # Simulate a response from Claude
        await self._send_stream.send(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "Sure, I can do that. I will send some events now.",
                        }
                    ],
                    "model": "mock-model",
                },
            }
        )
        await asyncio.sleep(1)
        # Simulate a server notification
        await self._send_stream.send(
            {
                "type": "notification",
                "method": "log/info",
                "params": {"message": "Process starting..."},
            }
        )
        await asyncio.sleep(1)
        # Simulate an elicitation request
        await self._send_stream.send(
            {
                "type": "elicitation_request",
                "id": "elicit-abc-123",
                "prompt": "What is the magic word?",
            }
        )
        await asyncio.sleep(1)
        # Simulate a final result
        await self._send_stream.send(
            {
                "type": "result",
                "subtype": "success",
                "session_id": "mock-session",
                "num_turns": 3,
                "duration_ms": 3000,
                "duration_api_ms": 0,
                "is_error": False,
            }
        )

    def receive_messages(self):
        return self._receive_stream


async def main():
    """Main function to run the bidirectional client example."""
    print("--- Claude SDK Bidirectional Client Example ---")

    # Initialize the client, passing handlers to the constructor
    client = ClaudeSDKClient(
        on_notification=handle_notification,
        on_elicitation_request=handle_elicitation,
    )

    # --- Manually mock the transport layer ---
    # In a real application, you would not do this. The client would connect
    # to the actual Claude Code service.
    mock_transport = MockTransport()

    def mock_transport_factory(*args, **kwargs):
        return mock_transport

    # In a real application, the client would use the real transport. For this
    # example, we patch the transport class to return our mock instance.
    with patch(
        "claude_code_sdk.client.SubprocessCLITransport",
        return_value=mock_transport,
    ):
        async with client:
            print("\nSending initial query to the client...")
            await client.query("Please start a process that requires my input.")

        print("\nWaiting for responses from the client...")
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"[ASSISTANT] {block.text}")
            elif isinstance(message, ResultMessage):
                print(f"\n[RESULT] Conversation finished.")

    # After the conversation, we can check if our elicitation handler's
    # response was "sent" back through the mock transport.
    print("\n--- Verification ---")
    mock_transport.send_elicitation_response.assert_awaited_once()
    print("Elicitation response was successfully sent back to the transport.")
    print("Example finished.")


if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        print("\nExample cancelled by user.")
