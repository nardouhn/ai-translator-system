from fastapi import APIRouter, Depends, File as FastAPIFile, Form, Header, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.concurrency import run_in_threadpool
import hashlib

from app.db.models import File, FileSegment, Logs, StatusEnum, RequestTypeEnum
from app.db.session import get_async_db
from app.services.rate_limit_service import check_rate_limit
from app.services.session_service import SessionService

router = APIRouter()

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


@router.post("/file/translate")
async def file_translate_api(
    upload_file: UploadFile = FastAPIFile(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    domain: str | None = Form(default=None),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_async_db),
):
    file_content = await upload_file.read()
    file_size = len(file_content)
    await upload_file.seek(0)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds 20MB limit.",
        )

    filename = upload_file.filename or "unknown"
    ext = filename.split('.')[-1].lower()
    if ext not in ['pdf', 'docx', 'txt']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .pdf, .docx, and .txt are allowed.",
        )

    session_id = x_session_id
    if not session_id:
        session_id = await db.run_sync(
            lambda session: SessionService.create_session(db=session, ip_address=None, user_agent=None)
        )
    
    check_rate_limit(session_id)

    file_data = {
        "session_id": session_id,
        "file_size": file_size,
    }
    if hasattr(File, "filename"):
        file_data["filename"] = filename
    else:
        file_data["original_filename"] = filename
    if hasattr(File, "status"):
        file_data["status"] = "pending"

    file_row = File(**file_data)
    db.add(file_row)
    await db.commit()
    await db.refresh(file_row)

    from app.services.document_translator import convert_pdf_to_docx, translate_docx_document, translate_txt_document
    from app.services.translator_provider import translate_batch_with_provider

    segments_list = []
    
    async def _do_translate_batch(texts: list[str]) -> list[str]:
        if not texts:
            return []
        translated_texts, _ = await translate_batch_with_provider(texts, source_lang, target_lang, domain or "General")
        for orig, tr in zip(texts, translated_texts):
            segments_list.append({
                "source_text": orig,
                "translated_text": tr
            })
        return translated_texts

    async def _do_translate(text: str) -> str:
        res = await _do_translate_batch([text])
        return res[0] if res else text

    # Perform document translation asynchronously
    if ext == "txt":
        full_text, b64_data = await translate_txt_document(file_content, _do_translate)
    elif ext == "docx" or ext == "pdf":
        if ext == "pdf":
            docx_bytes = await run_in_threadpool(convert_pdf_to_docx, file_content)
        else:
            docx_bytes = file_content
        full_text, b64_data = await translate_docx_document(docx_bytes, _do_translate_batch)
    else:
        full_text, b64_data = "", ""
        
    file_id_val_inner = getattr(file_row, "file_id", getattr(file_row, "id", None))
    
    # Save segments asynchronously
    for index, seg in enumerate(segments_list):
        segment_data = {
            "file_id": file_id_val_inner,
            "segment_order": index,
            "translated_text": seg['translated_text']
        }
        if hasattr(FileSegment, "content"):
            segment_data["content"] = seg['source_text']
        else:
            segment_data["source_text"] = seg['source_text']
        if hasattr(FileSegment, "status"):
            segment_data["status"] = "done"
        
        db.add(FileSegment(**segment_data))
        
    await db.flush()

    if hasattr(File, "status"):
        file_row.status = StatusEnum.success
    
    file_id_val = getattr(file_row, "id", getattr(file_row, "file_id", None))
    await db.commit()
    
    log_record = Logs(
        session_id=session_id,
        translation_id=None,
        status=StatusEnum.success,
        request_type=RequestTypeEnum.file,
    )
    db.add(log_record)
    await db.commit()

    return {
        "file_id": file_id_val,
        "translated_text": full_text,
        "file_content_b64": b64_data,
    }
