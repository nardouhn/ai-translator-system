import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from app.api.v1.file_translate import router as file_translate_router
from app.api.v1.translate import router as translate_router
from app.api.v1.health import router as health_router
from app.api.v1.admin import router as admin_router

app = FastAPI()

frontend_url = os.getenv("FRONTEND_URL", "*")
allow_origins = [url.strip() for url in frontend_url.split(",")] if frontend_url != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(translate_router, prefix="/api/v1")
app.include_router(file_translate_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "API is running"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
