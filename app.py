import os
import shutil
import tempfile
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

from services.resume_service import ResumeReviewService

# 1. Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger("api")

# Metrics
UPLOADED_FILE_SIZE = Histogram(
    "uploaded_file_size_bytes",
    "Size of uploaded resume files in bytes",
    buckets=[100_000, 500_000, 1_000_000, 2_000_000, 5_000_000]
)
RESUME_REVIEWS_TOTAL = Counter(
    "resume_reviews_total",
    "Total number of resume reviews processed",
    ["status"]
)
REVIEW_GENERATION_TIME = Histogram(
    "review_generation_seconds",
    "Time spent generating the resume review",
    buckets=[1, 5, 10, 20, 30, 45, 60, 90, 120]
)

# 2. Initialize App
app = FastAPI(
    title="Resume Reviewer API",
    description="Multimodal AI Backend for Resume Reviews",
    version="1.0.0"
)

# Instrument the app
Instrumentator().instrument(app).expose(app)

# 3. Initialize Service
try:
    resume_service = ResumeReviewService()
except Exception as e:
    logger.critical(f"Failed to initialize logic service: {e}")
    resume_service = None

def cleanup_temp_file(path: str):
    """Background task to remove temporary file."""
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Cleaned up temporary file: {path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {path}: {e}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Resume Reviewer API"}

@app.post("/api/v1/review")
async def review_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a PDF resume to get an AI-powered review.
    """
    logger.info(f"Received file upload: {file.filename}, Content-Type: {file.content_type}")

    # Validation
    if file.content_type != "application/pdf":
        RESUME_REVIEWS_TOTAL.labels(status="failed_type").inc()
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is supported.")
    
    # 5MB limit
    MAX_FILE_SIZE = 5 * 1024 * 1024
    if file.size and file.size > MAX_FILE_SIZE:
        RESUME_REVIEWS_TOTAL.labels(status="failed_size").inc()
        logger.error(f"File too large: {file.size} bytes. Maximum size is 5MB.")
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5MB.")
    
    # Record file size
    if file.size:
        UPLOADED_FILE_SIZE.observe(file.size)

    if not resume_service:
        RESUME_REVIEWS_TOTAL.labels(status="failed_service").inc()
        logger.error("Service not initialized properly.")
        raise HTTPException(status_code=503, detail="Service not initialized properly.")

    # Save to temp file
    try:
        # Create a temp file with .pdf suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
            logger.info(f"Saved upload to temporary path: {tmp_path}")
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail="Could not save uploaded file.")

    # Process
    try:
        # Service is now async to prevent blocking loop during network calls/PDF processing
        with REVIEW_GENERATION_TIME.time():
            review_result = await resume_service.review_resume(tmp_path)
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_file, tmp_path)
        
        RESUME_REVIEWS_TOTAL.labels(status="success").inc()
        return {
            "filename": file.filename,
            "review": review_result
        }
        
    except Exception as e:
        # Ensure cleanup happens even on error
        background_tasks.add_task(cleanup_temp_file, tmp_path)
        logger.error(f"Processing error: {e}")
        RESUME_REVIEWS_TOTAL.labels(status="failed_processing").inc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
