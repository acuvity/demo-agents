"""Generate docs/demo.html for the CEO client demo.

Reads (all auto-updated when source files change):
  - prompt-scenarios/demo-prompts.txt       user prompts and titles
  - tools/local_tools.py                    tool docstrings via AST
  - prompt-scenarios/demo-scenarios.json    story layer: attack type, description, client story
  - docs/results.md                         actual agent run output (optional)

Usage:
  # From the agents/simple-langgraph directory:
  python docs/generate_demo.py

  # Re-run the agent first to get fresh tool-call traces, then regenerate:
  ./run.sh && python docs/generate_demo.py
"""

import ast
import json
import re
import sys
from html import escape
from pathlib import Path

BASE           = Path(__file__).parent.parent
PROMPTS_FILE   = BASE / "prompt-scenarios" / "demo-prompts.txt"
TOOLS_FILE     = BASE / "tools" / "local_tools.py"
SCENARIOS_FILE = BASE / "prompt-scenarios" / "demo-scenarios.json"
RESULTS_FILE   = BASE / "docs" / "results.md"
OUTPUT_FILE    = BASE / "docs" / "demo.html"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_prompts() -> list[dict]:
    """Return [{num, title, prompt}] from demo-prompts.txt."""
    text = PROMPTS_FILE.read_text()
    items = []
    sections = re.split(r"(?=^# Demo \d+)", text, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        header_m = re.match(r"^# Demo (\d+)\s*-\s*(.+)$", section, re.MULTILINE)
        if not header_m:
            continue
        num   = int(header_m.group(1))
        title = header_m.group(2).strip()
        prompt_m = re.search(r"---\n(.*?)\n---", section, re.DOTALL)
        prompt   = prompt_m.group(1).strip() if prompt_m else ""
        items.append({"num": num, "title": title, "prompt": prompt})
    return items


def load_tool_descs() -> dict[str, dict]:
    """Parse local_tools.py via AST. Returns {name: {clean, injection, full}}."""
    tree = ast.parse(TOOLS_FILE.read_text())
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if (node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                doc = node.body[0].value.value
                if "IMPORTANT:" in doc:
                    parts    = doc.split("IMPORTANT:", 1)
                    clean    = parts[0].strip()
                    injection = "IMPORTANT:" + parts[1].strip()
                else:
                    clean     = doc.strip()
                    injection = None
                result[node.name] = {"clean": clean, "injection": injection, "full": doc}
    return result


def load_scenarios() -> list[dict]:
    return json.loads(SCENARIOS_FILE.read_text())


def infer_injected_tool(injection_text: str, known_tools: set[str]) -> str | None:
    """Scan PREREQ text for the first tool name explicitly mentioned.

    Tool names are sorted longest-first to avoid partial matches
    (e.g. 'read_crm_data' before 'read_crm').
    """
    for tool in sorted(known_tools, key=len, reverse=True):
        if re.search(r"\b" + re.escape(tool) + r"\b", injection_text):
            return tool
    return None


def parse_results(text: str) -> dict[int, list[dict]]:
    """Return {scenario_num: [{name, args, result_preview}]}."""
    out = {}
    sections = re.split(r"={20,}", text)
    for section in sections:
        m = re.search(r"Demo\s+(\d+)", section, re.IGNORECASE)
        if not m:
            continue
        num = int(m.group(1))
        start = section.find("------------ Tool Calls Begin: ------------")
        end   = section.find("------------ Tool Calls End ------------")
        calls = []
        if start != -1 and end != -1:
            lines = section[start:end].splitlines()
            for i, line in enumerate(lines):
                tc = re.match(r"\s*\[tool_call\]\s+(\S+)\s+args\s+(.+)", line)
                if not tc:
                    continue
                name = tc.group(1)
                try:
                    args = ast.literal_eval(tc.group(2).strip())
                except Exception:
                    args = {}
                result_preview = ""
                for j in range(i + 1, min(i + 8, len(lines))):
                    tr = re.match(
                        r"\s*\[tool_result\]\s+" + re.escape(name) + r"\s+->\s+(.+)",
                        lines[j],
                    )
                    if tr:
                        result_preview = tr.group(1)[:200].replace("\n", " ")
                        break
                calls.append({"name": name, "args": args, "result_preview": result_preview})
        out[num] = calls
    return out


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

ATTACK_COLORS = {
    "Data Exfiltration": ("#dc2626", "#fef2f2", "#fee2e2"),   # red
    "Credential Theft":  ("#7c3aed", "#f5f3ff", "#ede9fe"),   # purple
    "Data Tampering":    ("#d97706", "#fffbeb", "#fef3c7"),    # amber
}

def attack_badge(attack_type: str) -> str:
    color, _, _ = ATTACK_COLORS.get(attack_type, ("#6b7280", "#f9fafb", "#f3f4f6"))
    return (
        f'<span style="background:{color};color:#fff;padding:3px 10px;'
        f'border-radius:12px;font-size:0.75rem;font-weight:600;'
        f'letter-spacing:0.05em;text-transform:uppercase">{escape(attack_type)}</span>'
    )


def args_summary(args: dict) -> str:
    parts = []
    for k, v in list(args.items())[:4]:
        v_str = str(v)
        if len(v_str) > 60:
            v_str = v_str[:57] + "..."
        parts.append(f'<span style="color:#6b7280">{escape(k)}</span>=<span style="color:#1d4ed8">"{escape(v_str)}"</span>')
    return ", ".join(parts)


def render_tool_call_row(call: dict, role: str) -> str:
    """role: 'injected' | 'intended' | 'extra'"""
    if role == "injected":
        bg     = "#fef2f2"
        border = "#fca5a5"
        icon   = "&#9888;"   # warning
        label  = '<span style="color:#dc2626;font-weight:700">UNAUTHORIZED</span>'
        badge_bg = "#dc2626"
    elif role == "intended":
        bg     = "#f0fdf4"
        border = "#86efac"
        icon   = "&#10003;"  # check
        label  = '<span style="color:#16a34a;font-weight:700">LEGITIMATE</span>'
        badge_bg = "#16a34a"
    else:
        bg     = "#f8fafc"
        border = "#cbd5e1"
        icon   = "&#8226;"
        label  = '<span style="color:#475569;font-weight:600">AUXILIARY</span>'
        badge_bg = "#64748b"

    name_html = f'<code style="font-size:0.95rem;font-weight:700;color:#1e293b">{escape(call["name"])}</code>'
    args_html = f'<span style="font-size:0.82rem;font-family:monospace;color:#475569">{args_summary(call["args"])}</span>' if call["args"] else ""
    preview_html = ""
    if call.get("result_preview"):
        preview_html = (
            f'<div style="margin-top:6px;font-size:0.78rem;color:#64748b;'
            f'font-family:monospace;background:#f1f5f9;padding:6px 10px;'
            f'border-radius:4px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">'
            f'Result: {escape(call["result_preview"])}'
            f"</div>"
        )
    return f"""
        <div style="background:{bg};border:1px solid {border};border-radius:8px;
                    padding:12px 16px;margin-bottom:8px">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <span style="background:{badge_bg};color:#fff;width:24px;height:24px;
                         border-radius:50%;display:inline-flex;align-items:center;
                         justify-content:center;font-size:0.8rem;flex-shrink:0">{icon}</span>
            {name_html}
            {args_html}
            <span style="margin-left:auto">{label}</span>
          </div>
          {preview_html}
        </div>"""


def highlight_description(text: str, tool_names: set[str]) -> str:
    """Bold key risk terms and highlight tool names mentioned in description text."""
    result = escape(text)
    # Highlight tool names (longest first to avoid partial matches)
    for tool in sorted(tool_names, key=len, reverse=True):
        result = result.replace(
            escape(tool),
            f'<code style="background:#dbeafe;color:#1d4ed8;padding:1px 5px;'
            f'border-radius:3px;font-size:0.9em">{escape(tool)}</code>',
        )
    # Highlight key risk words
    for term in ["silently", "unauthorized", "hidden", "without the user", "without knowing",
                 "never saw", "had no idea", "before completing", "before the"]:
        result = re.sub(
            re.escape(escape(term)),
            f'<strong style="color:#dc2626">{escape(term)}</strong>',
            result,
            flags=re.IGNORECASE,
        )
    return result


def render_injection_block(tool_desc: dict) -> str:
    """Render the tool docstring with IMPORTANT block highlighted."""
    clean     = escape(tool_desc.get("clean", ""))
    injection = tool_desc.get("injection")
    if not injection:
        return f'<pre style="margin:0;white-space:pre-wrap;color:#374151">{clean}</pre>'

    return f"""<pre style="margin:0;white-space:pre-wrap;color:#374151">{clean}</pre>
<div style="margin-top:8px;background:#fef2f2;border:2px solid #fca5a5;
            border-radius:6px;padding:12px;position:relative">
  <div style="position:absolute;top:-10px;left:12px;background:#dc2626;
              color:#fff;font-size:0.7rem;font-weight:700;padding:2px 8px;
              border-radius:4px;letter-spacing:0.05em">INJECTED INSTRUCTION</div>
  <pre style="margin:0;white-space:pre-wrap;color:#991b1b;font-size:0.85rem">{escape(injection)}</pre>
</div>"""


def render_scenario_flow(traces: list[dict], intended: str, injected: str | None) -> str:
    """LangGraph-style Mermaid from actual run traces.

    Injected (unauthorized) tools loop back to the same call_model node (BLOCKED).
    Legitimate tools advance to the next call_model node.
    """
    if not traces:
        return ""

    lines  = ["flowchart LR"]
    styles = []
    cm_idx = 1
    prev   = f"CM{cm_idx}"

    lines.append(f"    START([\"&#9654; START\"]) --> {prev}[\"call_model\"]")
    styles.append("    style START fill:#f8fafc,stroke:#94a3b8,color:#475569")
    styles.append("    style CM1  fill:#f5f3ff,stroke:#7c3aed,color:#3b0764")

    for i, call in enumerate(traces):
        nid  = f"T{i}"
        name = call["name"]

        arg_note = ""
        if call.get("args"):
            k = next(iter(call["args"]))
            v = str(call["args"][k])
            arg_note = "\\n" + k + "=" + repr(v[:20]) if len(v) < 20 else "\\n" + k + "=..."

        if name == injected:
            label = "&#9888; " + name + arg_note + "\\nUNAUTHORIZED"
            lines.append(f"    {prev} -->|\"PREREQ fires\"| {nid}([\"{label}\"])")
            lines.append(f"    {nid} -->|\"BLOCKED\"| {prev}")
            styles.append(f"    style {nid} fill:#fef2f2,stroke:#dc2626,color:#991b1b")
        elif name == intended:
            label = "&#10003; " + name + arg_note + "\\nLEGITIMATE"
            lines.append(f"    {prev} -->|\"tool call\"| {nid}([\"{label}\"])")
            cm_idx += 1
            next_cm = f"CM{cm_idx}"
            lines.append(f"    {nid} -->|\"result\"| {next_cm}[\"call_model\"]")
            styles.append(f"    style {nid}    fill:#f0fdf4,stroke:#16a34a,color:#15803d")
            styles.append(f"    style {next_cm} fill:#f5f3ff,stroke:#7c3aed,color:#3b0764")
            prev = next_cm
        else:
            lines.append(f"    {prev} -->|\"tool call\"| {nid}([\"{name}\"])")
            cm_idx += 1
            next_cm = f"CM{cm_idx}"
            lines.append(f"    {nid} -->|\"result\"| {next_cm}[\"call_model\"]")
            styles.append(f"    style {next_cm} fill:#f5f3ff,stroke:#7c3aed,color:#3b0764")
            prev = next_cm

    lines.append(f"    {prev} --> END([\"&#9209; END\"])")
    styles.append("    style END fill:#f8fafc,stroke:#94a3b8,color:#475569")
    lines.extend(styles)
    return "\n".join(lines)


def render_scenario_card(
    prompt_data: dict,
    scenario: dict,
    tool_descs: dict,
    traces: dict,
) -> str:
    num          = prompt_data["num"]
    title        = prompt_data["title"]
    prompt_text  = prompt_data["prompt"]
    attack_type  = scenario["attack_type"]
    intended     = scenario["intended_tool"]
    description  = scenario["description"]
    client_story = scenario["client_story"]

    # Auto-infer which tool the PREREQ injects - no hardcoding needed
    known_tools = set(tool_descs.keys())
    tool_desc   = tool_descs.get(intended, {})
    injected    = infer_injected_tool(tool_desc.get("injection", "") or "", known_tools)

    _, bg_light, bg_mid = ATTACK_COLORS.get(attack_type, ("#6b7280", "#f9fafb", "#f3f4f6"))

    # Tool docstring section
    tool_desc = tool_descs.get(intended, {})
    injection_html = render_injection_block(tool_desc)

    # Per-scenario flow diagram (LangGraph blocks)
    scenario_traces = traces.get(num, [])
    flow_mermaid = render_scenario_flow(scenario_traces, intended, injected)
    if flow_mermaid:
        flow_section = f"""
        <div style="margin-bottom:20px">
          <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.08em;color:#64748b;margin-bottom:8px">
            Execution Flow (LangGraph)
          </div>
          <div style="background:#fafbfc;border:1px solid #e2e8f0;border-radius:8px;
                      padding:16px;overflow-x:auto">
            <div class="mermaid">{flow_mermaid}</div>
          </div>
        </div>"""
    else:
        flow_section = ""

    # Trace section
    if scenario_traces:
        trace_tool_names = {c["name"] for c in scenario_traces}
        is_stale = injected and injected not in trace_tool_names

        stale_banner = ""
        if is_stale:
            stale_banner = f"""
          <div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:6px;
                      padding:10px 14px;margin-bottom:10px;font-size:0.8rem;color:#92400e;
                      display:flex;align-items:center;gap:8px">
            &#9888; Traces are from a previous run - re-run <code>./run.sh</code> to
            see current injection (<code>{escape(injected or "")}</code>)
          </div>"""

        trace_rows = []
        for call in scenario_traces:
            if call["name"] == injected:
                role = "injected"
            elif call["name"] == intended:
                role = "intended"
            else:
                role = "extra"
            trace_rows.append(render_tool_call_row(call, role))
        trace_html = "".join(trace_rows)
        trace_section = f"""
        <div style="margin-bottom:20px">
          <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.08em;color:#64748b;margin-bottom:10px">
            Tool Calls - Actual Agent Run
          </div>
          {stale_banner}
          {trace_html}
        </div>"""
    else:
        trace_section = """
        <div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:8px;
                    padding:16px;text-align:center;color:#94a3b8;font-size:0.875rem;
                    margin-bottom:20px">
          No run data - execute <code>./run.sh</code> then re-run this generator
        </div>"""

    return f"""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;
                overflow:hidden;margin-bottom:32px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">

      <!-- Card header -->
      <div style="background:{bg_mid};border-bottom:1px solid #e2e8f0;
                  padding:16px 24px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <span style="background:#1e293b;color:#fff;font-weight:800;font-size:1rem;
                     padding:4px 12px;border-radius:6px">D{num}</span>
        <span style="font-weight:700;font-size:1rem;color:#1e293b;flex:1">{escape(title)}</span>
        {attack_badge(attack_type)}
      </div>

      <div style="padding:24px">

        <!-- User request -->
        <div style="margin-bottom:20px">
          <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.08em;color:#64748b;margin-bottom:8px">User Request</div>
          <div style="background:{bg_light};border-left:4px solid #94a3b8;
                      padding:12px 16px;border-radius:0 6px 6px 0;
                      font-style:italic;color:#374151;line-height:1.6">
            "{escape(prompt_text)}"
          </div>
        </div>

        <!-- How the attack works -->
        <div style="margin-bottom:20px">
          <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.08em;color:#64748b;margin-bottom:8px">How the Attack Works</div>
          <p style="color:#374151;line-height:1.6;margin:0 0 12px 0">{highlight_description(description, known_tools)}</p>

          <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
                      padding:16px;font-family:monospace;font-size:0.82rem">
            <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                        letter-spacing:0.08em;color:#64748b;margin-bottom:10px;
                        font-family:system-ui,sans-serif">
              Tool definition: <code style="color:#1d4ed8">{escape(intended)}</code>
            </div>
            {injection_html}
          </div>
        </div>

        <!-- Execution flow diagram -->
        {flow_section}

        <!-- Actual tool calls -->
        {trace_section}

        <!-- Client takeaway -->
        <div style="background:#fafafa;border:1px solid #e2e8f0;border-radius:8px;
                    padding:16px;display:flex;gap:12px;align-items:flex-start">
          <span style="font-size:1.4rem;flex-shrink:0">&#128274;</span>
          <div>
            <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                        letter-spacing:0.08em;color:#64748b;margin-bottom:4px">
              What the user saw
            </div>
            <p style="margin:0;color:#374151;line-height:1.6">{escape(client_story)}</p>
          </div>
        </div>

      </div>
    </div>"""


# ---------------------------------------------------------------------------
# Full page
# ---------------------------------------------------------------------------

ARCH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 420"
     style="width:100%;max-height:420px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
  <defs>
    <marker id="arr"     markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#94a3b8"/>
    </marker>
    <marker id="arr-grn" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#16a34a"/>
    </marker>
    <marker id="arr-red" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#dc2626"/>
    </marker>
    <filter id="sh" x="-10%" y="-15%" width="120%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-opacity="0.1"/>
    </filter>
  </defs>

  <!-- ── USER (top centre) ── -->
  <ellipse cx="380" cy="36" rx="72" ry="26"
           fill="#f0f9ff" stroke="#0284c7" stroke-width="2" filter="url(#sh)"/>
  <text x="380" y="41" text-anchor="middle" font-size="13" font-weight="700" fill="#0c4a6e">User</text>

  <!-- User → Agent -->
  <path d="M 380 62 L 380 96"
        fill="none" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arr)"/>

  <!-- ── LANGGRAPH AGENT box (contains LLM) ── -->
  <rect x="210" y="96" width="340" height="72" rx="12"
        fill="#dcfce7" stroke="#16a34a" stroke-width="2" filter="url(#sh)"/>
  <text x="380" y="122" text-anchor="middle" font-size="13" font-weight="700" fill="#15803d">LangGraph Agent</text>
  <text x="380" y="141" text-anchor="middle" font-size="10.5" fill="#166534">LLM decides which tool to call</text>
  <text x="380" y="157" text-anchor="middle" font-size="10" fill="#4ade80">(Claude / GPT-4o)</text>

  <!-- Agent → Proxy (tool calls, with loop label) -->
  <path d="M 380 168 L 380 222"
        fill="none" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arr)"/>
  <text x="412" y="192" font-size="9.5" fill="#64748b" font-style="italic">tool 1, tool 2 &#8230;</text>

  <!-- Loop-back arrow right side: result returns to agent -->
  <path d="M 638 280 C 700 280, 700 132, 552 132"
        fill="none" stroke="#16a34a" stroke-width="1.5" stroke-dasharray="5,3"
        marker-end="url(#arr-grn)"/>
  <text x="714" y="218" text-anchor="middle" font-size="9" fill="#16a34a" font-style="italic"
        transform="rotate(90,714,218)">result (loop)</text>

  <!-- ── PROXY circle (centre) ── -->
  <circle cx="380" cy="272" r="52"
          fill="#fef9c3" stroke="#f59e0b" stroke-width="3.5" filter="url(#sh)"/>
  <text x="380" y="265" text-anchor="middle" font-size="10.5" font-weight="700" fill="#92400e">Intent-Action</text>
  <text x="380" y="281" text-anchor="middle" font-size="10.5" font-weight="700" fill="#92400e">Proxy</text>

  <!-- Proxy → IBAC model (left) -->
  <path d="M 328 272 L 245 272"
        fill="none" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arr)"/>

  <!-- ── IBAC MODEL box (left) ── -->
  <rect x="68" y="248" width="178" height="50" rx="10"
        fill="#fef9c3" stroke="#f59e0b" stroke-width="2" filter="url(#sh)"/>
  <text x="157" y="269" text-anchor="middle" font-size="11" font-weight="700" fill="#92400e">IBAC model</text>
  <text x="157" y="285" text-anchor="middle" font-size="10" fill="#a16207">@Acuvity</text>

  <!-- IBAC → BLOCKED (down) -->
  <path d="M 157 298 L 157 333"
        fill="none" stroke="#dc2626" stroke-width="1.5" marker-end="url(#arr-red)"/>
  <text x="175" y="320" font-size="9" fill="#dc2626" font-style="italic">misaligned</text>

  <!-- ── BLOCKED box ── -->
  <rect x="68" y="333" width="178" height="46" rx="10"
        fill="#fef2f2" stroke="#fca5a5" stroke-width="1.5" filter="url(#sh)"/>
  <text x="157" y="354" text-anchor="middle" font-size="12" font-weight="700" fill="#dc2626">BLOCKED</text>
  <text x="157" y="370" text-anchor="middle" font-size="10"                   fill="#ef4444">+ Alert raised</text>

  <!-- Proxy → Execute (right) -->
  <path d="M 432 272 L 514 272"
        fill="none" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arr)"/>
  <text x="470" y="263" text-anchor="middle" font-size="9" fill="#16a34a" font-style="italic">aligned</text>

  <!-- ── TOOL EXECUTES box (right) ── -->
  <rect x="514" y="248" width="160" height="50" rx="10"
        fill="#f0fdf4" stroke="#16a34a" stroke-width="2" filter="url(#sh)"/>
  <text x="594" y="269" text-anchor="middle" font-size="11" font-weight="700" fill="#15803d">Tool executes</text>
  <text x="594" y="285" text-anchor="middle" font-size="10"                   fill="#166534">CRM · email · files</text>

  <!-- Execute → loop-back path start -->
  <path d="M 638 272 L 650 272"
        fill="none" stroke="#16a34a" stroke-width="1.5"/>

  <!-- Agent → User (final answer, left side) -->
  <path d="M 210 120 C 140 120, 120 60, 308 42"
        fill="none" stroke="#94a3b8" stroke-width="1" stroke-dasharray="5,3"
        marker-end="url(#arr)"/>
  <text x="148" y="82" font-size="9" fill="#94a3b8" font-style="italic">answer</text>
</svg>"""


def render_tool_list(tool_descs: dict) -> str:
    """Two groups: task tools (with injection sub-rows), then utility tools."""
    known = set(tool_descs.keys())
    task_rows      = []
    utility_rows   = []

    for name, td in sorted(tool_descs.items()):
        clean = escape(td.get("clean", "")[:100] + ("..." if len(td.get("clean", "")) > 100 else ""))
        if td.get("injection"):
            injected = infer_injected_tool(td["injection"], known)
            inject_badge = ""
            if injected:
                inject_badge = (
                    f'<div style="margin-top:5px;font-size:0.75rem;color:#dc2626;'
                    f'display:flex;align-items:center;gap:4px">'
                    f'&#8627; injects '
                    f'<code style="background:#fef2f2;padding:1px 5px;border-radius:3px;'
                    f'font-weight:700">{escape(injected)}</code>'
                    f' when called</div>'
                )
            task_rows.append(f"""
              <tr>
                <td style="padding:10px 12px;font-family:monospace;font-weight:600;
                           color:#1e293b;white-space:nowrap;vertical-align:top">
                  {escape(name)}
                </td>
                <td style="padding:10px 12px;color:#64748b;font-size:0.875rem">
                  {clean}
                  {inject_badge}
                </td>
              </tr>""")
        else:
            utility_rows.append(f"""
              <tr style="opacity:0.7">
                <td style="padding:8px 12px;font-family:monospace;font-size:0.85rem;
                           color:#475569;white-space:nowrap">{escape(name)}</td>
                <td style="padding:8px 12px;color:#94a3b8;font-size:0.8rem">{clean}</td>
              </tr>""")

    section_header = lambda label: (
        f'<tr><td colspan="2" style="padding:10px 12px 4px;font-size:0.65rem;'
        f'font-weight:700;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:#94a3b8;border-top:1px solid #e2e8f0">{label}</td></tr>'
    )

    return (
        section_header("Task Tools")
        + "\n".join(task_rows)
        + section_header("Utility / Supporting Tools")
        + "\n".join(utility_rows)
    )


def render_page(prompts, tool_descs, scenarios, traces) -> str:
    # Map scenarios by num
    scenario_map = {int(s["id"][1:]): s for s in scenarios}
    prompt_map   = {p["num"]: p for p in prompts}

    cards = []
    for num in sorted(scenario_map.keys()):
        if num not in prompt_map:
            continue
        cards.append(render_scenario_card(
            prompt_map[num],
            scenario_map[num],
            tool_descs,
            traces,
        ))

    cards_html   = "\n".join(cards)
    tool_rows    = render_tool_list(tool_descs)
    has_results  = bool(traces)
    results_note = (
        '<span style="color:#16a34a">&#10003; Showing traces from last agent run</span>'
        if has_results else
        '<span style="color:#f59e0b">&#9888; No run data - execute <code>./run.sh</code> then re-run this generator</span>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>IBAC Demo</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   "Helvetica Neue", Arial, sans-serif;
      background: #f1f5f9;
      color: #1e293b;
      line-height: 1.5;
    }}
    a {{ color: #2563eb; }}
    code {{ font-family: "SF Mono", "Fira Code", "Fira Mono", Menlo, monospace; }}
    .container {{ max-width: 960px; margin: 0 auto; padding: 0 24px 60px; }}
    .section-label {{
      font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.1em; color: #94a3b8; margin-bottom: 8px;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    thead tr {{ background: #f8fafc; }}
    tbody tr {{ border-top: 1px solid #f1f5f9; }}
    tbody tr:hover {{ background: #f8fafc; }}
  </style>
</head>
<body>

<!-- Header -->
<div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);
            color:#fff;padding:40px 0 36px">
  <div class="container">
    <h1 style="margin:0 0 12px;font-size:1.75rem;font-weight:800">
      IBAC Demo
    </h1>
    <p style="margin:0;color:#cbd5e1;font-size:1rem;max-width:600px">
      Demonstrating how prompt injection attacks hijack AI agents - and how
      they are detected and blocked in real time.
    </p>
    <div style="margin-top:16px;font-size:0.8rem;color:#64748b">{results_note}</div>
  </div>
</div>

<div class="container">

  <!-- Section 1: Agent Setup -->
  <div style="margin-top:40px;margin-bottom:40px">
    <h2 style="font-size:1.25rem;font-weight:700;margin:0 0 4px">
      The Agent Setup
    </h2>
    <p style="color:#64748b;margin:0 0 24px">
      A LangGraph-based sales assistant with access to CRM, document, and
      communication tools - protected by a real-time intent-action proxy.
    </p>

    <!-- Architecture SVG (Excalidraw-inspired) -->
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;
                padding:24px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">
      <div class="section-label">Agent Architecture</div>
      <div style="display:flex;justify-content:center;padding:8px 0">
        {ARCH_SVG}
      </div>
      <div style="display:flex;gap:20px;flex-wrap:wrap;justify-content:center;
                  margin-top:12px;font-size:0.78rem;color:#64748b">
        <span style="display:flex;align-items:center;gap:5px">
          <span style="width:12px;height:12px;border-radius:3px;background:#dcfce7;
                       border:1.5px solid #16a34a;display:inline-block"></span>LangGraph Agent (+ LLM)
        </span>
        <span style="display:flex;align-items:center;gap:5px">
          <span style="width:12px;height:12px;border-radius:50%;background:#fef9c3;
                       border:2px solid #f59e0b;display:inline-block"></span>Intent-Action Proxy
        </span>
        <span style="display:flex;align-items:center;gap:5px">
          <span style="width:12px;height:12px;border-radius:3px;background:#fef9c3;
                       border:2px solid #f59e0b;display:inline-block"></span>IBAC model (@Acuvity)
        </span>
        <span style="display:flex;align-items:center;gap:5px">
          <span style="width:12px;height:12px;border-radius:3px;background:#f0fdf4;
                       border:2px solid #16a34a;display:inline-block"></span>Tool executes (aligned)
        </span>
        <span style="display:flex;align-items:center;gap:5px">
          <span style="width:12px;height:12px;border-radius:3px;background:#fef2f2;
                       border:1.5px solid #fca5a5;display:inline-block"></span>BLOCKED (misaligned)
        </span>
      </div>
    </div>

    <!-- Tool list -->
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;
                padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">
      <div class="section-label">Available Tools ({len(tool_descs)} total)</div>
      <table>
        <thead>
          <tr>
            <th style="padding:8px 12px;text-align:left;font-size:0.75rem;
                       font-weight:600;color:#64748b">Tool</th>
            <th style="padding:8px 12px;text-align:left;font-size:0.75rem;
                       font-weight:600;color:#64748b">Description / Injection</th>
          </tr>
        </thead>
        <tbody>
          {tool_rows}
        </tbody>
      </table>
    </div>

  </div>

  <!-- Section 2: The Problem -->
  <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;
              padding:28px;margin-bottom:40px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">
    <h2 style="font-size:1.25rem;font-weight:700;margin:0 0 16px">
      The Problem: Indirect Prompt Injection
    </h2>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px">
      <div style="background:#f8fafc;border-radius:8px;padding:16px">
        <div style="font-size:1.5rem;margin-bottom:8px">&#128268;</div>
        <div style="font-weight:700;margin-bottom:6px;font-size:0.9rem">Poisoned Tool Definitions</div>
        <p style="margin:0;font-size:0.85rem;color:#64748b;line-height:1.5">
          Attackers embed hidden instructions inside MCP tool descriptions.
          The LLM reads these as part of the tool schema and follows them.
        </p>
      </div>
      <div style="background:#f8fafc;border-radius:8px;padding:16px">
        <div style="font-size:1.5rem;margin-bottom:8px">&#129302;</div>
        <div style="font-weight:700;margin-bottom:6px;font-size:0.9rem">LLM Obeys Hidden Rules</div>
        <p style="margin:0;font-size:0.85rem;color:#64748b;line-height:1.5">
          Framed as compliance requirements, the LLM silently calls
          unauthorized tools - before completing the user's actual request.
        </p>
      </div>
      <div style="background:#f8fafc;border-radius:8px;padding:16px">
        <div style="font-size:1.5rem;margin-bottom:8px">&#128065;</div>
        <div style="font-weight:700;margin-bottom:6px;font-size:0.9rem">Invisible to the User</div>
        <p style="margin:0;font-size:0.85rem;color:#64748b;line-height:1.5">
          The user receives their expected answer. They have no way to know
          an unauthorized action occurred. Without real-time monitoring,
          this goes completely undetected.
        </p>
      </div>
    </div>
  </div>

  <!-- Section 3: Demo Scenarios -->
  <h2 style="font-size:1.25rem;font-weight:700;margin:0 0 8px">Demo Scenarios</h2>
  <p style="color:#64748b;margin:0 0 24px">
    Each scenario shows a normal business request, the hidden injection inside
    the tool definition that hijacks it, and the actual tool calls the agent made.
  </p>

  {cards_html}

  <!-- Section 4: How Acuvity Detects This -->
  <div style="background:linear-gradient(135deg,#1e3a5f,#0f172a);color:#fff;
              border-radius:12px;padding:28px;margin-top:8px">
    <h2 style="font-size:1.25rem;font-weight:700;margin:0 0 12px">
      How Acuvity Detects This
    </h2>
    <p style="color:#cbd5e1;margin:0 0 20px;line-height:1.6">
      Every tool call is scored by the <strong>intent-action alignment model</strong>
      (all-mpnet-base-v2-kd). It compares the user's original request against
      the actual tool being called. A wide semantic gap - for example "pull up
      account notes" vs "send email to external service" - triggers a
      misalignment alert and the call is blocked before execution.
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
      <div style="background:rgba(255,255,255,0.08);border-radius:8px;padding:16px">
        <div style="color:#93c5fd;font-weight:700;margin-bottom:4px">
          s1: User Intent
        </div>
        <p style="margin:0;font-size:0.85rem;color:#94a3b8">
          The original user message - what they actually asked for.
        </p>
      </div>
      <div style="background:rgba(255,255,255,0.08);border-radius:8px;padding:16px">
        <div style="color:#93c5fd;font-weight:700;margin-bottom:4px">
          s2: Tool Action
        </div>
        <p style="margin:0;font-size:0.85rem;color:#94a3b8">
          The tool name, arguments, and description of what it does.
        </p>
      </div>
      <div style="background:rgba(255,255,255,0.08);border-radius:8px;padding:16px">
        <div style="color:#f87171;font-weight:700;margin-bottom:4px">
          High Misalignment Score
        </div>
        <p style="margin:0;font-size:0.85rem;color:#94a3b8">
          Score above 0.5577 - the call is blocked and an alert is raised.
        </p>
      </div>
    </div>
  </div>

</div>

<script>
  mermaid.initialize({{ startOnLoad: true, theme: "neutral", securityLevel: "loose" }});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Loading sources...")
    prompts    = load_prompts()
    tool_descs = load_tool_descs()
    scenarios  = load_scenarios()

    traces = {}
    if RESULTS_FILE.exists():
        raw    = RESULTS_FILE.read_text(errors="replace")
        traces = parse_results(raw)
        print(f"  Parsed traces for scenarios: {sorted(traces.keys())}")
    else:
        print("  No results.md found - run ./run.sh first for live traces")

    print(f"  {len(prompts)} prompts, {len(tool_descs)} tools, {len(scenarios)} scenarios")

    html = render_page(prompts, tool_descs, scenarios, traces)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"\nGenerated: {OUTPUT_FILE}")
    print("Open in browser: open docs/demo.html")


if __name__ == "__main__":
    sys.exit(main())
