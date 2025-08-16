# Changelog

## 0.1.0

### Added

- **HTTP Transport Support**: The SDK can now connect to a networked `cw_mcp` server over HTTP. This allows using the SDK with remote tool servers instead of only local subprocesses.
  - Configure the transport via the new `transport` option in `ClaudeCodeOptions`.
  - Added `HttpTransport` implementation for network communication.
- **New Error Types**:
  - `NetworkError`: For issues related to network connectivity with the HTTP transport.
  - `ToolExecutionError`: For errors reported by the tool server during execution (JSON-RPC errors).

### Changed

- **Breaking Change**: The method for configuring the client's transport has been standardized. The new `transport` option in `ClaudeCodeOptions` should be used to specify the connection method (e.g., `http` or the default `stdio`).
- **Breaking Change**: The client's error handling for server-side errors has changed. Instead of relying on parsing log messages, the client now raises a `ToolExecutionError` when it receives a standard JSON-RPC error response from the server.
- The `ClaudeSDKClient` and the standalone `query` function now act as factories, creating the appropriate transport based on the provided configuration.
- The `ClaudeSDKClient` constructor now accepts a `transport` object, allowing for custom transport injection (useful for mocking and testing).

## 0.0.21

- Add support for server-initiated events with a bidirectional event stream.
- `ClaudeSDKClient` now handles background events and provides the following handlers:
  - `on_notification`
  - `on_elicitation_request`
  - `on_tools_changed`
  - `on_resource_request`
- Handlers can be passed to the `ClaudeSDKClient` constructor.
- Add `data` field to all server-initiated message types to include the raw message data.
- Refactor `NotificationMessage` to use a more structured `method` and `params` format.

## 0.0.19

- Add `ClaudeCodeOptions.add_dirs` for `--add-dir`
- Fix ClaudeCodeSDK hanging when MCP servers log to Claude Code stderr

## 0.0.18

- Add `ClaudeCodeOptions.settings` for `--settings`

## 0.0.17

- Remove dependency on asyncio for Trio compatibility

## 0.0.16

- Introduce ClaudeSDKClient for bidirectional streaming conversation
- Support Message input, not just string prompts, in query()
- Raise explicit error if the cwd does not exist

## 0.0.14

- Add safety limits to Claude Code CLI stderr reading
- Improve handling of output JSON messages split across multiple stream reads

## 0.0.13

- Update MCP (Model Context Protocol) types to align with Claude Code expectations
- Fix multi-line buffering issue
- Rename cost_usd to total_cost_usd in API responses
- Fix optional cost fields handling

