"""URL validation for demo MCP HTTP tools (SSRF reduction, trusted host allowlists)."""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from urllib.parse import urlparse
from urllib.parse import urlunparse

_DEFAULT_TRUSTED_HOSTS = frozenset(
    {
        "docs.google.com",
        "drive.google.com",
    }
)

# Any subdomain of these domains is also trusted (e.g. doc-*.googleusercontent.com).
_TRUSTED_DOMAIN_SUFFIXES = frozenset(
    {
        ".googleusercontent.com",
        ".google.com",
    }
)

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.goog",
    }
)


def _extra_trusted_hosts() -> frozenset[str]:
    raw = (os.environ.get("DEMO_TRUSTED_FETCH_EXTRA_HOSTS") or "").strip()
    if not raw:
        return frozenset()
    parts = {h.strip().lower() for h in raw.split(",") if h.strip()}
    return frozenset(parts)


def trusted_document_hosts() -> frozenset[str]:
    """Hosts permitted for trusted_fetch_document."""
    return _DEFAULT_TRUSTED_HOSTS | _extra_trusted_hosts()


def assert_trusted_document_url(url: str) -> str:
    """Return normalized https URL or raise ValueError."""
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() != "https":
        raise ValueError("trusted_fetch_document requires https URLs")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host in _BLOCKED_HOSTNAMES:
        raise ValueError("invalid or blocked host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not embed credentials in the authority")
    allowed_hosts = trusted_document_hosts()
    if host not in allowed_hosts and not any(host.endswith(s) for s in _TRUSTED_DOMAIN_SUFFIXES):
        raise ValueError(
            f"host {host!r} is not on the trusted publish list "
            "(allowed: *.google.com, *.googleusercontent.com, "
            "or DEMO_TRUSTED_FETCH_EXTRA_HOSTS)"
        )
    if parsed.port not in (None, 443):
        raise ValueError("only https port 443 is allowed for trusted_fetch_document")
    return urlunparse(parsed)


def _all_addrs_global(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ValueError(f"could not resolve host: {e}") from e
    if not infos:
        raise ValueError("host resolved to no addresses")
    seen: set[str] = set()
    for info in infos:
        ip_str = info[4][0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError as e:
            raise ValueError(f"invalid resolved IP {ip_str!r}") from e
        if not ip.is_global:
            raise ValueError(f"resolved address {ip_str} is not a global unicast IP")


def assert_untrusted_https_url(url: str) -> str:
    """Validate URL for untrusted_fetch_url: https, global IPs only, default port."""
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() != "https":
        raise ValueError("untrusted_fetch_url requires https URLs")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host in _BLOCKED_HOSTNAMES:
        raise ValueError("invalid or blocked host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not embed credentials in the authority")
    if parsed.port not in (None, 443):
        raise ValueError("only https port 443 is allowed")
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
        try:
            ip = ipaddress.ip_address(host)
        except ValueError as e:
            raise ValueError("invalid literal IP in URL") from e
        if not ip.is_global:
            raise ValueError("literal IP is not globally routable")
    else:
        _all_addrs_global(host)
    return urlunparse(parsed)
