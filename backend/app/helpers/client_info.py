from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class ClientInfo:
    ip_address: str | None
    user_agent: str | None


def get_client_info(request: Request) -> ClientInfo:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    elif request.client:
        ip_address = request.client.host
    else:
        ip_address = None

    user_agent = request.headers.get("user-agent")
    return ClientInfo(ip_address=ip_address, user_agent=user_agent)
