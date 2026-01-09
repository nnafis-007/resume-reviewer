import os
import shutil
import tempfile
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

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

# 2. Initialize App
app = FastAPI(
    title="Resume Reviewer API",
    description="Multimodal AI Backend for Resume Reviews",
    version="1.0.0"
)

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
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is supported.")
    
    if not resume_service:
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
        review_result = resume_service.review_resume(tmp_path)
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_file, tmp_path)
        
        return {
            "filename": file.filename,
            "review": review_result
        }
        
    except Exception as e:
        # Ensure cleanup happens even on error
        background_tasks.add_task(cleanup_temp_file, tmp_path)
        logger.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
