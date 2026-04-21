from fastapi import APIRouter, Depends, File as FastAPIFile, Form, Header, HTTPException, UploadFile, status
from sqlalchemy.orm import Session as ORMSession

from app.db.models import File, FileSegment, Logs, StatusEnum
from app.db.session import get_db
from app.services.file_parser import extract_text
from app.services.rate_limit_service import check_rate_limit
from app.services.session_service import SessionService
from app.services.text_splitter import split_text
from app.services.translation_service import translate_text

router = APIRouter()

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024


@router.post("/file/translate")
async def file_translate_api(
    upload_file: UploadFile = FastAPIFile(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    domain: str | None = Form(default=None),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: ORMSession = Depends(get_db),
):
    file_content = await upload_file.read()
    file_size = len(file_content)
    await upload_file.seek(0)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be <= 15MB",
        )

    session_id = x_session_id or SessionService.create_session(db=db, ip_address=None, user_agent=None)
    check_rate_limit(session_id)

    file_data = {
        "session_id": session_id,
        "file_size": file_size,
    }
    if hasattr(File, "filename"):
        file_data["filename"] = upload_file.filename
    else:
        file_data["original_filename"] = upload_file.filename
    if hasattr(File, "status"):
        file_data["status"] = "uploaded"

    file_row = File(**file_data)
    db.add(file_row)
    db.commit()
    db.refresh(file_row)

    extracted_text = await extract_text(upload_file)
    segments = split_text(extracted_text)

    file_segments: list[FileSegment] = []
    for index, segment in enumerate(segments):
        segment_data = {
            "file_id": file_row.file_id,
            "segment_order": index,
        }
        if hasattr(FileSegment, "content"):
            segment_data["content"] = segment
        else:
            segment_data["source_text"] = segment
        if hasattr(FileSegment, "status"):
            segment_data["status"] = "pending"
        file_segments.append(FileSegment(**segment_data))

    if file_segments:
        db.add_all(file_segments)
        db.flush()

    for segment_row in file_segments:
        source_segment_text = getattr(segment_row, "content", None) or getattr(segment_row, "source_text", "") or ""
        result = translate_text(
            db=db,
            session_id=session_id,
            source_text=source_segment_text,
            source_lang=source_lang,
            target_lang=target_lang,
            domain=domain,
            auto_commit=False,
        )
        segment_row.translated_text = result["translated_text"]
        if hasattr(FileSegment, "status"):
            segment_row.status = "done"

    sorted_segments = sorted(file_segments, key=lambda x: x.segment_order)
    translated_segments = [
        segment.translated_text for segment in sorted_segments
    ]

    if hasattr(File, "status"):
        file_row.status = "completed"

    db.commit()
    log_record = Logs(
        session_id=session_id,
        translation_id=None,
        status=StatusEnum.success,
    )
    db.add(log_record)
    db.commit()

    return {
        "file_id": getattr(file_row, "id", file_row.file_id),
        "translated_text": " ".join(translated_segments).strip(),
    }
