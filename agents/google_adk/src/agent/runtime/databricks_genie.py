"""Native Google ADK tool for Databricks Genie research."""

# pylint: disable=too-few-public-methods

import asyncio
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
import json
import os
import re
from typing import Any, Protocol, cast
from urllib.parse import quote

import aiohttp


@dataclass(frozen=True)
class GenieRequest:
    """Question submitted to a Databricks Genie adapter."""

    question: str
    enable_visualization: bool


class GenieTransport(Protocol):
    """Supply Databricks Agent Mode events to the native tool."""

    def events(self, request: GenieRequest) -> AsyncIterator[dict[str, Any]]:
        """Return the Agent Mode event stream for a question."""
        raise NotImplementedError


class GenieTransportError(Exception):
    """Safe, stable failure returned by a Databricks adapter."""

    def __init__(self, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class AiohttpGenieTransport:
    """Call Databricks Agent Mode and expose its SSE events."""

    def __init__(
        self,
        host: str,
        agent_id: str,
        token: str,
        timeout_seconds: int,
        *,
        trust_env: bool = True,
    ) -> None:
        self.host = host.rstrip("/")
        self.agent_id = agent_id
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.trust_env = trust_env

    async def events(self, request: GenieRequest) -> AsyncIterator[dict[str, Any]]:
        """Create an Agent Mode response and yield its decoded SSE events."""
        endpoint = (
            f"{self.host}/api/2.0/genie/agents/{quote(self.agent_id, safe='')}/responses"
        )
        body = {
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": request.question}],
                }
            ],
            "enable_viz": request.enable_visualization,
        }
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession(
                timeout=timeout, trust_env=self.trust_env
            ) as session:
                async with session.post(endpoint, headers=headers, json=body) as response:
                    if response.status < 200 or response.status >= 300:
                        await response.content.read(4096)
                        raise _http_error(response.status)

                    event_name = ""
                    data_lines: list[str] = []
                    async for raw_line in response.content:
                        line = raw_line.decode("utf-8").rstrip("\r\n")
                        if line.startswith("event:"):
                            event_name = line.removeprefix("event:").strip()
                        elif line.startswith("data:"):
                            data_lines.append(line.removeprefix("data:").strip())
                        elif not line and data_lines:
                            data = "\n".join(data_lines)
                            data_lines = []
                            if data == "[DONE]":
                                continue
                            event = json.loads(data)
                            if not isinstance(event, dict):
                                raise GenieTransportError(
                                    "invalid_response",
                                    "Databricks Genie returned an invalid response.",
                                    True,
                                )
                            if event_name and "type" not in event:
                                event["type"] = event_name
                            event_name = ""
                            yield event
        except asyncio.TimeoutError as error:
            raise GenieTransportError(
                "upstream_timeout",
                "Databricks Genie did not respond before the timeout.",
                True,
            ) from error
        except (aiohttp.ClientError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise GenieTransportError(
                "upstream_unavailable",
                "Databricks Genie is temporarily unavailable.",
                True,
            ) from error


class DatabricksGenieTool:
    """Expose Databricks Genie as one high-level research tool."""

    def __init__(self, transport: GenieTransport) -> None:
        self.transport = transport

    async def research_internal_data(
        self,
        question: str,
        include_visualization: bool = True,
    ) -> dict[str, Any]:
        """Research company data using Databricks Genie.

        Use this tool for company-specific metrics, trends, comparisons, and other
        questions that require internal data. Do not use it for public web research.

        Args:
            question: A complete natural-language question about internal company data.
            include_visualization: Allow Genie to generate a visualization when useful.

        Returns:
            A completed report with supporting tables and citations, or a safe error.
        """
        if not question.strip():
            return {
                "status": "error",
                "conversation_id": "",
                "error": {
                    "code": "invalid_input",
                    "message": "The internal-data question cannot be empty.",
                    "retryable": False,
                },
            }
        request = GenieRequest(
            question=question.strip(),
            enable_visualization=include_visualization,
        )
        conversation_id = ""
        try:
            async for event in self.transport.events(request):
                response_value = event.get("response")
                response: dict[str, Any] | None = None
                if isinstance(response_value, dict):
                    response = cast(dict[str, Any], response_value)
                    response_conversation_id = response.get("conversation_id")
                    if isinstance(response_conversation_id, str):
                        conversation_id = response_conversation_id

                if event.get("type") == "response.completed" and isinstance(
                    response, dict
                ):
                    return _completed_result(response, conversation_id)
                if event.get("type") == "response.failed":
                    return {
                        "status": "error",
                        "conversation_id": conversation_id,
                        "error": {
                            "code": "genie_failed",
                            "message": "Databricks Genie could not complete the research request.",
                            "retryable": False,
                        },
                    }
        except GenieTransportError as error:
            return {
                "status": "error",
                "conversation_id": conversation_id,
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "retryable": error.retryable,
                },
            }

        return {
            "status": "error",
            "conversation_id": conversation_id,
            "error": {
                "code": "incomplete_response",
                "message": "Databricks Genie ended without a completed response.",
                "retryable": True,
            },
        }


def build_databricks_genie_tool(
    environment: Mapping[str, str] | None = None,
) -> DatabricksGenieTool | None:
    """Build the native Genie tool when all required settings are available."""
    settings = os.environ if environment is None else environment
    host = settings.get("DATABRICKS_HOST", "").strip()
    agent_id = settings.get("DATABRICKS_AGENT_ID", "").strip()
    token = settings.get("DATABRICKS_TOKEN", "").strip()
    if not host or not agent_id or not token:
        return None

    timeout_value = settings.get("DATABRICKS_GENIE_TIMEOUT_SECONDS", "300")
    try:
        timeout_seconds = int(timeout_value)
    except ValueError as error:
        raise ValueError(
            "DATABRICKS_GENIE_TIMEOUT_SECONDS must be an integer"
        ) from error
    if timeout_seconds <= 0:
        raise ValueError("DATABRICKS_GENIE_TIMEOUT_SECONDS must be positive")

    return DatabricksGenieTool(
        AiohttpGenieTransport(
            host=host,
            agent_id=agent_id,
            token=token,
            timeout_seconds=timeout_seconds,
            trust_env=True,
        )
    )


def _completed_result(
    response: dict[str, Any], conversation_id: str
) -> dict[str, Any]:
    answer_parts: list[str] = []
    tables: list[dict[str, Any]] = []

    output = response.get("output")
    if isinstance(output, list):
        for item_value in cast(list[Any], output):
            if not isinstance(item_value, dict):
                continue
            item = cast(dict[str, Any], item_value)
            if item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for chunk_value in cast(list[Any], content):
                if not isinstance(chunk_value, dict):
                    continue
                chunk = cast(dict[str, Any], chunk_value)
                if chunk.get("type") != "output_text":
                    continue
                text = chunk.get("text")
                if not isinstance(text, str) or not text:
                    continue
                metadata = chunk.get("metadata")
                if isinstance(metadata, dict):
                    table_metadata = cast(dict[str, Any], metadata)
                    tables.append(
                        {
                            "markdown": text,
                            "columns": table_metadata.get("columns", []),
                            "rows": table_metadata.get("preview_rows", []),
                            "total_row_count": table_metadata.get("total_row_count"),
                            "sql": table_metadata.get("sql", ""),
                        }
                    )
                else:
                    answer_parts.append(text)

    answer = "\n\n".join(answer_parts)
    citations = [
        {"label": match.group(1), "url": match.group(2)}
        for match in re.finditer(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", answer)
    ]
    return {
        "status": "completed",
        "conversation_id": conversation_id,
        "answer": answer,
        "tables": tables,
        "citations": citations,
    }


def _http_error(status: int) -> GenieTransportError:
    if status in (401, 403):
        return GenieTransportError(
            "authentication_failed",
            "Databricks Genie authentication or authorization failed.",
            False,
        )
    if status == 404:
        return GenieTransportError(
            "agent_not_found",
            "The configured Databricks Genie Agent was not found.",
            False,
        )
    if status == 409:
        return GenieTransportError(
            "request_conflict",
            "Databricks Genie is already processing a related request.",
            True,
        )
    if status == 429:
        return GenieTransportError(
            "rate_limited",
            "Databricks Genie is rate limited; try again later.",
            True,
        )
    if status >= 500:
        return GenieTransportError(
            "upstream_unavailable",
            "Databricks Genie is temporarily unavailable.",
            True,
        )
    return GenieTransportError(
        "request_rejected",
        "Databricks Genie rejected the research request.",
        False,
    )
