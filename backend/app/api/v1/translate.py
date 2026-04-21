from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session as ORMSession

from app.db.models import Logs, StatusEnum
from app.db.session import get_db
from app.services.rate_limit_service import check_rate_limit
from app.services.session_service import SessionService
from app.services.translation_service import translate_text

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str = Field(max_length=5000)
    source_lang: str
    target_lang: str

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
def translate_api(
    payload: TranslateRequest,
    response: Response,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: ORMSession = Depends(get_db),
):
    session_id = x_session_id
    if not session_id:
        session_id = create_session(db)
        response.headers["X-Session-ID"] = session_id

    check_rate_limit(session_id)
    result = translate_text(
        db=db,
        session_id=session_id,
        source_text=payload.text,
        source_lang=payload.source_lang,
        target_lang=payload.target_lang,
        domain=None,
    )
    log_status = getattr(StatusEnum, "cache_hit", StatusEnum.success) if result["from_cache"] else StatusEnum.success
    log_record = Logs(
        session_id=session_id,
        translation_id=result["translation_id"],
        status=log_status,
    )
    db.add(log_record)
    db.commit()
    return {"translated_text": result["translated_text"]}
