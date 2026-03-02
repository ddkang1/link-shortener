import ipaddress
import re
import secrets
import socket
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import URL


# Private/loopback IP ranges to block (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
    ipaddress.ip_network("10.0.0.0/8"),        # private
    ipaddress.ip_network("172.16.0.0/12"),     # private
    ipaddress.ip_network("192.168.0.0/16"),    # private
    ipaddress.ip_network("169.254.0.0/16"),    # link-local
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]


def _is_private_ip(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in _BLOCKED_NETWORKS)
    except ValueError:
        pass

    # Try DNS resolution
    try:
        resolved = socket.getaddrinfo(host, None)
        for entry in resolved:
            ip_str = entry[4][0]
            try:
                addr = ipaddress.ip_address(ip_str)
                if any(addr in net for net in _BLOCKED_NETWORKS):
                    return True
            except ValueError:
                continue
    except (socket.gaierror, OSError):
        pass

    return False


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    host = parsed.hostname

    if not host:
        raise HTTPException(status_code=422, detail="Cannot extract host from URL")

    if _is_private_ip(host):
        raise HTTPException(status_code=400, detail="URLs pointing to private/loopback IPs are not allowed")


def shorten_url(db: Session, original_url: str, base_url: str) -> URL:
    validate_url(original_url)

    # Generate a unique short code (retry on collision)
    for _ in range(10):
        code = secrets.token_urlsafe(6)
        existing = db.query(URL).filter(URL.short_code == code).first()
        if not existing:
            break
    else:
        raise HTTPException(status_code=500, detail="Failed to generate unique short code")

    url_obj = URL(original_url=original_url, short_code=code)
    db.add(url_obj)
    db.commit()
    db.refresh(url_obj)
    return url_obj


def get_url_by_code(db: Session, short_code: str) -> URL:
    url_obj = db.query(URL).filter(URL.short_code == short_code).first()
    if not url_obj:
        raise HTTPException(status_code=404, detail="Short code not found")
    return url_obj


def increment_and_redirect(db: Session, short_code: str) -> str:
    url_obj = get_url_by_code(db, short_code)
    url_obj.click_count += 1
    db.commit()
    return url_obj.original_url


def get_stats(db: Session, short_code: str) -> URL:
    return get_url_by_code(db, short_code)
