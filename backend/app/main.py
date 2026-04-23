import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from app.api.v1.file_translate import router as file_translate_router
from app.api.v1.translate import router as translate_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(translate_router, prefix="/api/v1")
app.include_router(file_translate_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "API is running"}
