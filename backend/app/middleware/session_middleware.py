from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.db.session import SessionLocal
from app.dependencies.session_context import SESSION_HEADER_NAME, get_or_create_session


class SessionContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        db = SessionLocal()
        try:
            session_id = get_or_create_session(request=request, db=db)
        finally:
            db.close()

        response = await call_next(request)
        response.headers[SESSION_HEADER_NAME] = str(session_id)
        return response
