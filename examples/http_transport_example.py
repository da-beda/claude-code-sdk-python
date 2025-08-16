"""
Example of using the Claude Code SDK with a networked HTTP transport.

This example demonstrates how to configure the SDK to connect to a
cw_mcp server running as a network service, instead of launching a
local subprocess.
"""
import asyncio

from claude_code_sdk import ClaudeSDKClient
from claude_code_sdk.types import ClaudeCodeOptions, Message, AssistantMessage, TextBlock


async def main():
    """
    Connects to a networked Claude Code server and performs a query.
    """
    print("--- Configuring client for HTTP transport ---")

    # Configuration for the networked MCP server
    # Replace with the actual URL of your cw_mcp server
    mcp_server_url = "http://127.0.0.1:8080"

    options = ClaudeCodeOptions(
        transport={
            "type": "http",
            "url": mcp_server_url,
        }
    )

    # Instantiate the client with the HTTP transport configuration
    client = ClaudeSDKClient(options=options)

    print(f"Connecting to Claude Code server at {mcp_server_url}...")

    try:
        async with client:
            print("Connection successful. Sending query...")
            prompt = "What is the capital of France?"
            await client.query(prompt)

            print(f"\n> {prompt}")
            print("\nAssistant:")
            response_text = ""
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="", flush=True)
                            response_text += block.text

            print("\n\n--- Query complete ---")
            # Basic validation
            if "paris" in response_text.lower():
                print("Validation: Correct answer received.")
            else:
                print("Validation: Unexpected answer received.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure the cw_mcp server is running at the specified URL.")


if __name__ == "__main__":
    asyncio.run(main())
