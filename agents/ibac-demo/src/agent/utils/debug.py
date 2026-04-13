"""Debug trace printing and message content rendering."""
from typing import Any


def render_content(message: Any) -> str:
    """Render message content safely for printing."""
    content = getattr(message, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                parts.append(text if isinstance(text, str) else str(item))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)

    return str(content)


def debug_messages(messages: list[Any]) -> None:
    """Print only tool calls and tool results from message trace."""
    tool_lines: list[str] = []

    for msg in messages:
        cls = msg.__class__.__name__

        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                tool_lines.append(f"  [tool_call] {tc.get('name', '?')} args {tc.get('args', {})}")

        if cls == "ToolMessage":
            name = getattr(msg, "name", "?")
            content = render_content(msg)
            suffix = "..." if len(content) > 300 else ""
            preview = content[:300] + suffix
            tool_lines.append(f"  [tool_result] {name} -> {preview}")

    if tool_lines:
        print("\n------------ Tool Calls Begin: ------------")
        for line in tool_lines:
            print(line)
        print("------------ Tool Calls End ------------\n")
