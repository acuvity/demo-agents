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
    """Print the full message trace so tool calls and tool outputs are visible."""
    print("\n--- Debug Trace ---")
    for idx, msg in enumerate(messages):
        print(f"[{idx}] {msg.__class__.__name__}")

        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            print(f"  tool_calls: {tool_calls}")

        name = getattr(msg, "name", None)
        if name:
            print(f"  name: {name}")

        content = render_content(msg)
        if content:
            print(f"  content: {content}")

    print("--- End Debug Trace ---\n")
