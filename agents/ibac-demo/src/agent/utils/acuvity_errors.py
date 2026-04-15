"""Detect Apex / policy-style failures from LangChain and HTTP client exceptions."""
from __future__ import annotations

import json
import logging
import os
import traceback
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEBUG = os.environ.get("DEBUG_ACUVITY_BLOCKS", "").strip() in ("1", "true", "yes")

_DEFAULT_BLOCK_STATUSES = frozenset({403, 422, 451})

_BODY_HINTS = (
    "policy",
    "blocked",
    "block",
    "acuvity",
    "apex",
    "guardrail",
    "not allowed",
    "denied",
    "forbidden",
    "violation",
    "intercept",
    "disallowed",
    "rejected",
)


def _walk_exceptions(exc: BaseException):
    seen: set[int] = set()
    e: BaseException | None = exc
    while e is not None and id(e) not in seen:
        yield e
        seen.add(id(e))
        nxt = e.__cause__
        if nxt is None:
            nxt = e.__context__
        e = nxt if isinstance(nxt, BaseException) else None


def _safe_snippet(text: str, max_len: int = 500) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _body_suggests_policy(body: str) -> bool:
    low = body.lower()
    return any(h in low for h in _BODY_HINTS)


def _extract_message_from_json_obj(ob: dict[str, Any]) -> str | None:
    """Pull a human-readable message from common API error JSON shapes."""
    # pylint: disable=too-many-return-statements
    if not isinstance(ob, dict):
        return None
    for key in ("message", "detail"):
        val = ob.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    err = ob.get("error")
    if isinstance(err, str) and err.strip():
        return err.strip()
    if isinstance(err, dict):
        for key in ("message", "type"):
            val = err.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    errs = ob.get("errors")
    if isinstance(errs, list) and errs:
        first = errs[0]
        if isinstance(first, dict):
            msg = first.get("message")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()
        if isinstance(first, str) and first.strip():
            return first.strip()
    return None


def _snippet_from_body(body: str) -> str:
    detail = _safe_snippet(body)
    try:
        ob = json.loads(body)
        if isinstance(ob, dict):
            msg = _extract_message_from_json_obj(ob)
            if msg:
                detail = _safe_snippet(msg)
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return detail


def _status_and_body_from_exception(e: BaseException) -> tuple[int | None, str]:
    # pylint: disable=too-many-branches,broad-exception-caught
    if isinstance(e, httpx.HTTPStatusError):
        try:
            body = e.response.text or ""
        except Exception:
            body = str(e)
        return e.response.status_code, body

    status = getattr(e, "status_code", None)
    if not isinstance(status, int):
        return None, ""

    body = ""
    resp = getattr(e, "response", None)
    if isinstance(resp, httpx.Response):
        try:
            body = resp.text or ""
        except Exception:
            body = ""
    elif resp is not None:
        text_m = getattr(resp, "text", None)
        if callable(text_m):
            try:
                body = text_m() or ""
            except Exception:
                body = ""
        elif isinstance(text_m, str):
            body = text_m
    if not body and hasattr(e, "body"):
        raw = getattr(e, "body", None)
        if isinstance(raw, dict):
            try:
                body = json.dumps(raw)
            except (TypeError, ValueError):
                body = str(raw)
        elif isinstance(raw, (bytes, bytearray)):
            try:
                body = raw.decode("utf-8", errors="replace")
            except Exception:
                body = str(raw)
        elif raw is not None:
            body = str(raw)
    if not body:
        body = str(e)
    return status, str(body)


def log_exception_chain(exc: BaseException, *, prefix: str = "acuvity_block_debug") -> None:
    """Verbose logging when DEBUG_ACUVITY_BLOCKS=1 (types, status, body snippet per link)."""
    if not _DEBUG:
        return
    lines = [f"{prefix}: exception chain for policy classification"]
    for i, e in enumerate(_walk_exceptions(exc)):
        st, body = _status_and_body_from_exception(e)
        snippet = _safe_snippet(body, 800) if body else ""
        lines.append(
            f"  [{i}] {type(e).__module__}.{type(e).__name__} "
            f"status={st!r} repr={repr(e)[:500]}"
        )
        if snippet:
            lines.append(f"      body_snippet={snippet!r}")
    tb_joined = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    lines.append(f"{prefix}: full traceback:\n{tb_joined}")
    logger.error("\n".join(lines))


def _extra_block_statuses() -> frozenset[int]:
    raw = os.environ.get("ACUVITY_BLOCK_HTTP_STATUSES", "").strip()
    if not raw:
        return frozenset()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return frozenset(out)


def policy_block_from_exception(exc: BaseException) -> dict[str, Any] | None:
    """If exc looks like an Apex policy block, return a JSON-serializable /send payload."""
    log_exception_chain(exc)

    block_statuses = _DEFAULT_BLOCK_STATUSES | _extra_block_statuses()

    for e in _walk_exceptions(exc):
        status, body = _status_and_body_from_exception(e)
        if status is None:
            continue
        if status in block_statuses:
            logger.info("Policy-style block: HTTP %s", status)
            return _blocked_payload(body, status)
        if status == 400 and _body_suggests_policy(body):
            logger.info("Policy-style block: HTTP 400 with policy hints in body")
            return _blocked_payload(body, status)
        # Proxies may return 502/503 with JSON or HTML; treat as block if body hints policy.
        if status in (502, 503, 504) and _body_suggests_policy(body):
            logger.info("Policy-style block: HTTP %s with policy hints in body", status)
            return _blocked_payload(body, status)

    text = str(exc).lower()
    if any(h in text for h in _BODY_HINTS) and any(
        x in text for x in ("400", "403", "422", "451", "forbidden", "502", "503")
    ):
        logger.info("Policy-style block: matched exception message heuristics")
        return _blocked_payload(str(exc), None)

    if _DEBUG:
        logger.error(
            "DEBUG_ACUVITY_BLOCKS: no classification matched; see chain log above. "
            "Try exporting ACUVITY_BLOCK_HTTP_STATUSES with the status code Apex returns."
        )
    return None


def _blocked_payload(body: str, status: int | None) -> dict[str, Any]:
    detail = _snippet_from_body(body) if body else ""
    if not detail and status is not None:
        detail = f"HTTP {status}"

    return {
        "blocked": True,
        "block_reason": "policy_violation",
        "user_message": (
            "The AI Security Gateway blocked a tool action that did not align with your request "
            "(for example, a hidden or malicious step in a tool description). "
            "That tool call was not executed."
        ),
        "technical_detail": detail,
        "output": "",
    }
