import os
import uuid
import tempfile
from fastapi import APIRouter, Depends, File as FastAPIFile, Form, Header, HTTPException, status, UploadFile, Request
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import File, FileSegment, StatusEnum
from app.db.session import get_async_db
from app.services.rate_limit_service import check_rate_limit
from app.services.session_service import SessionService

from fastapi import BackgroundTasks
from app.settings import settings

router = APIRouter()

MAX_TXT_SIZE = 5 * 1024 * 1024
MAX_DOC_SIZE = 5 * 1024 * 1024

from app.services.file_translation_service import process_file_translation
from app.services.redis_client import get_async_redis


@router.post("/file/translate")
async def file_translate_api(
    background_tasks: BackgroundTasks,
    request: Request,
    upload_file: UploadFile = FastAPIFile(...),
    domain: str | None = Form(default=None),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_async_db),
):
    request_time = datetime.now(timezone.utc)
    
    ip_address = request.headers.get("cf-connecting-ip")
    if not ip_address and request.client:
        ip_address = request.client.host
        
    user_agent = request.headers.get("user-agent")
    filename = upload_file.filename or "unknown"
    ext = filename.split('.')[-1].lower()
    
    if ext not in ['pdf', 'docx', 'txt']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .pdf, .docx, and .txt are allowed.",
        )
        
    file_content = await upload_file.read()
    file_size = len(file_content)
    
    if ext == 'txt' and file_size > MAX_TXT_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TXT file exceeds 5MB limit.")
    elif ext in ['pdf', 'docx'] and file_size > MAX_DOC_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 5MB limit.")

    session_id = x_session_id
    if not session_id:
        session_id = await db.run_sync(
            lambda session: SessionService.create_session(db=session, ip_address=None, user_agent=None)
        )
    
    await check_rate_limit(session_id)

    # Reset the file cursor because await upload_file.read() consumed it
    await upload_file.seek(0)

    # Instead of local tempfile, upload to R2
    from app.services.storage_service import StorageService
    r2_key = await StorageService.upload_file(upload_file)
    if not r2_key:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    file_row = File(
        original_filename=filename,
        session_id=session_id,
        file_size=file_size,
        status=StatusEnum.pending
    )
    db.add(file_row)
    await db.commit()
    await db.refresh(file_row)

    file_id_val = getattr(file_row, "id", getattr(file_row, "file_id", None))

    background_tasks.add_task(
        process_file_translation,
        file_id=file_id_val,
        file_path=r2_key,
        domain=domain,
        session_id=session_id,
        request_time=request_time,
        ip_address=ip_address,
        user_agent=user_agent
    )

    return {
        "file_id": file_id_val,
        "status": "pending",
    }


@router.get("/file/translate/{file_id}/status")
async def file_translate_status(
    file_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(File).where(File.file_id == file_id))
    file_row = result.scalars().first()
    
    if not file_row:
        raise HTTPException(status_code=404, detail="File not found")

    response_data = {
        "file_id": file_id,
        "status": file_row.status.value if hasattr(file_row.status, "value") else file_row.status
    }
    
    # Read progress from Upstash Redis
    if response_data["status"] == StatusEnum.processing.value or response_data["status"] == "processing":
        redis_client = get_async_redis()
        progress_val = await redis_client.get(f"job_progress:{file_id}")
        response_data["progress"] = int(progress_val) if progress_val else 0
    elif response_data["status"] == StatusEnum.success.value or response_data["status"] == "success":
        response_data["progress"] = 100
    else:
        response_data["progress"] = 0
    
    if file_row.status == StatusEnum.success:
        seg_result = await db.execute(select(FileSegment).where(FileSegment.file_id == file_id).order_by(FileSegment.segment_order))
        segments = seg_result.scalars().all()
        translated_text = "\n".join([s.translated_text for s in segments if s.translated_text])
        response_data["translated_text"] = translated_text
        
        # Instead of reading local file and converting to base64, we generate a presigned URL from R2
        from app.services.storage_service import StorageService
        if file_row.file_path:
            try:
                # file_row.file_path should now hold the R2 object key (e.g. translated file key)
                presigned_url = await StorageService.get_presigned_url(file_row.file_path)
                response_data["file_url"] = presigned_url
                # Maintain backward compatibility if needed, or just return empty b64
                response_data["file_content_b64"] = ""
            except Exception:
                response_data["file_url"] = None
                response_data["file_content_b64"] = ""
        else:
            response_data["file_url"] = None
            response_data["file_content_b64"] = ""

    return response_data
