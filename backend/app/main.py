from fastapi import FastAPI

from app.api.v1.file_translate import router as file_translate_router
from app.api.v1.translate import router as translate_router

app = FastAPI()

app.include_router(translate_router, prefix="/api/v1")
app.include_router(file_translate_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "API is running"}
