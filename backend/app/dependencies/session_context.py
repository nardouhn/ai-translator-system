from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session as ORMSession

from app.helpers.client_info import get_client_info
from app.services.session_service import SessionService

SESSION_HEADER_NAME = "X-Session-ID"


def get_or_create_session(request: Request, db: ORMSession) -> str:
    header_value = request.headers.get(SESSION_HEADER_NAME)
    if header_value:
        if SessionService.get_session(db, header_value):
            request.state.session_id = header_value
            return header_value

    client_info = get_client_info(request)
    session_id = SessionService.create_session(
        db=db,
        ip_address=client_info.ip_address,
        user_agent=client_info.user_agent,
    )
    request.state.session_id = session_id
    return session_id
