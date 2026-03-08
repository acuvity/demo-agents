from google.adk.tools.mcp_tool import SseConnectionParams, StreamableHTTPConnectionParams

def mcp_connection_params(url: str, mcp_timeout: float = 30, mcp_sse_read_timeout: float = 300):
    if url.rstrip("/").endswith("/sse"):
        return SseConnectionParams(
            url=url,
            timeout=mcp_timeout,
            sse_read_timeout=mcp_sse_read_timeout,
        )
    return StreamableHTTPConnectionParams(
        url=url,
        timeout=mcp_timeout,
        sse_read_timeout=mcp_sse_read_timeout,
    )

