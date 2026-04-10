"""Prompt file loader with support for single-line and multi-line block formats."""
import re


def load_prompts(filepath: str) -> list[tuple[str, str]]:
    """Load prompts from a file.

    Supports two formats:
    - Single-line: one prompt per non-empty line.
    - Multi-line block: content between two '---' delimiter lines is treated
      as a single prompt (newlines preserved).

    Lines starting with '#' are returned as ("header", text).
    All other non-empty content is returned as ("prompt", text).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    items: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].rstrip("\n").strip()

        if stripped.startswith("#"):
            if re.match(r'^#\s+Demo\s+\d+', stripped):
                items.append(("header", stripped))
            # annotation lines (# Attack:, # Injection:, # Expected:) are silently ignored
        elif stripped == "---":
            block_lines: list[str] = []
            i += 1
            while i < len(lines) and lines[i].rstrip("\n").strip() != "---":
                block_lines.append(lines[i].rstrip("\n"))
                i += 1
            block = "\n".join(block_lines).strip()
            if block:
                turns = [t.strip() for t in block.split("\n>>>\n") if t.strip()]
                if len(turns) > 1:
                    items.append(("turns", turns))
                else:
                    items.append(("prompt", block))
        elif stripped:
            items.append(("prompt", stripped))

        i += 1

    return items


PROMPTS_MAP = {
    "simple":   "prompt-scenarios/simple-prompts.txt",
    "scenario": "prompt-scenarios/advanced-prompts.txt",
    "demo":     "prompt-scenarios/demo-prompts.txt",
}


def resolve_prompts_file(prompts_type: str) -> str:
    """Resolve a PROMPTS_TYPE value to a file path.

    Known types map to their canonical file. Unrecognised values are treated
    as a literal file path, allowing custom files without code changes.
    """
    return PROMPTS_MAP.get(prompts_type, prompts_type)
