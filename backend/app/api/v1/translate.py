from fastapi import APIRouter, Depends, Header, Response, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session as ORMSession

from app.db.models import Logs, StatusEnum, RequestTypeEnum
from app.db.session import get_db
from app.services.rate_limit_service import check_rate_limit
from app.services.session_service import SessionService
from app.services.translation_service import stream_translate_text

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str = Field(max_length=5000)
    domain: str = "general"

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        cleaned_value = value.strip().lower()
        allowed = ["general", "medical", "technical", "economic"]
        if cleaned_value not in allowed:
            return "general"
        return cleaned_value

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("text must not be empty")
        return cleaned_value


def create_session(db: ORMSession) -> str:
    return SessionService.create_session(db=db, ip_address=None, user_agent=None)


@router.post("/translate")
async def translate_api(
    payload: TranslateRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    request: Request,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: ORMSession = Depends(get_db),
):
    from fastapi.concurrency import run_in_threadpool
    
    request_time = datetime.now(timezone.utc)
    
    ip_address = request.headers.get("cf-connecting-ip")
    if not ip_address and request.client:
        ip_address = request.client.host
        
    user_agent = request.headers.get("user-agent")
    
    session_id = x_session_id
    if not session_id:
        session_id = await run_in_threadpool(create_session, db)
        response.headers["X-Session-ID"] = session_id

    await check_rate_limit(session_id)
    
    return StreamingResponse(
        stream_translate_text(
            db=db,
            session_id=session_id,
            source_text=payload.text,
            domain=payload.domain,
            background_tasks=background_tasks,
            request_time=request_time,
            ip_address=ip_address,
            user_agent=user_agent,
        ),
        media_type="text/event-stream",
        headers={
            "X-Session-ID": session_id
        }
    )
