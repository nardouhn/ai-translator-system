from fastapi import HTTPException, UploadFile, status


async def extract_text(file: UploadFile) -> str:
    filename = file.filename or ""
    if not filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt files are supported",
        )

    content = await file.read()
    await file.seek(0)
    return content.decode("utf-8")
