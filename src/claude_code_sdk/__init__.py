"""Claude SDK for Python."""

from ._errors import (
    ClaudeSDKError,
    CLIConnectionError,
    CLIJSONDecodeError,
    CLINotFoundError,
    ProcessError,
)
from .client import ClaudeSDKClient
from .query import query
from .types import (
    AssistantMessage,
    ClaudeCodeOptions,
    ContentBlock,
    ElicitationRequestHandler,
    ElicitationRequestMessage,
    McpServerConfig,
    Message,
    NotificationHandler,
    NotificationMessage,
    PermissionMode,
    ResourceRequestHandler,
    ResourceRequestMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolsChangedHandler,
    ToolsChangedMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

__version__ = "0.0.20"

__all__ = [
    # Main exports
    "query",
    "ClaudeSDKClient",
    # Types
    "PermissionMode",
    "McpServerConfig",
    "UserMessage",
    "AssistantMessage",
    "SystemMessage",
    "ResultMessage",
    "Message",
    "ClaudeCodeOptions",
    "TextBlock",
    "ThinkingBlock",
    "ToolUseBlock",
    "ToolResultBlock",
    "ContentBlock",
    "NotificationMessage",
    "ElicitationRequestMessage",
    "ToolsChangedMessage",
    "ResourceRequestMessage",
    # Handlers
    "NotificationHandler",
    "ElicitationRequestHandler",
    "ToolsChangedHandler",
    "ResourceRequestHandler",
    # Errors
    "ClaudeSDKError",
    "CLIConnectionError",
    "CLINotFoundError",
    "ProcessError",
    "CLIJSONDecodeError",
]
