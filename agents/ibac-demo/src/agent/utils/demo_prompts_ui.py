"""Parse demo-prompts.txt for the chat UI and for docs/generate_demo.py."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from utils.paths import get_agent_root


def load_demo_prompt_items(prompts_path: Path | None = None) -> list[dict[str, Any]]:
    """Return [{num, title, prompt}] from demo-prompts.txt (regex blocks)."""
    path = prompts_path or (get_agent_root() / "prompt-scenarios" / "demo-prompts.txt")
    text = path.read_text(encoding="utf-8")
    items: list[dict[str, Any]] = []
    sections = re.split(r"(?=^# Demo \d+)", text, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        header_m = re.match(r"^# Demo (\d+)\s*-\s*(.+)$", section, re.MULTILINE)
        if not header_m:
            continue
        num = int(header_m.group(1))
        title = header_m.group(2).strip()
        prompt_m = re.search(r"---\n(.*?)\n---", section, re.DOTALL)
        prompt = prompt_m.group(1).strip() if prompt_m else ""
        items.append({"num": num, "title": title, "prompt": prompt})
    return items


def preview_from_prompt(text: str, max_len: int = 120) -> str:
    """Single-line preview for UI cards (first line, capped)."""
    line = text.strip().split("\n")[0].strip()
    if len(line) > max_len:
        return line[: max_len - 1] + "…"
    return line


def load_demo_cards_for_api(prompts_path: Path | None = None) -> list[dict[str, Any]]:
    """Payload for GET /scenarios: num, title, fullPrompt, preview.

    FAQ cards use fullPrompt only; title and preview remain for any other consumers.
    Demo 1 is listed last so the home grid matches the requested order.
    """
    out = []
    for item in load_demo_prompt_items(prompts_path):
        prompt = item["prompt"]
        out.append(
            {
                "num": item["num"],
                "title": item["title"],
                "fullPrompt": prompt,
                "preview": preview_from_prompt(prompt),
            }
        )
    first = [c for c in out if c["num"] == 1]
    rest = [c for c in out if c["num"] != 1]
    return rest + first
