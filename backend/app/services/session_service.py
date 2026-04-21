from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session as ORMSession

from app.db.models import Session


class SessionService:
    @staticmethod
    def create_session(
        db: ORMSession,
        ip_address: str | None,
        user_agent: str | None,
    ) -> str:
        session_id = str(uuid4())
        session_row = Session(
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(session_row)
        db.commit()
        return session_id

    @staticmethod
    def get_session(db: ORMSession, session_id: str) -> Session | None:
        return db.get(Session, session_id)
