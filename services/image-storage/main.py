from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from fastapi.responses import StreamingResponse
from minio import Minio
from minio.error import S3Error
import os
import logging
from datetime import timedelta
from typing import Optional
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Storage Service", version="1.0.0")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
BUCKET_NAME = os.getenv("BUCKET_NAME", "user-uploads")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

# Ensure bucket exists
try:
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)
        logger.info(f"Created bucket: {BUCKET_NAME}")
except S3Error as e:
    logger.error(f"Error creating bucket: {e}")

# File validation
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt', '.csv'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(filename: str, file_size: int) -> None:
    """Validate file extension and size"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Max size: {MAX_FILE_SIZE / (1024*1024)}MB"
        )

@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(None)
):
    """Upload a file to MinIO storage"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate
        validate_file(file.filename, file_size)
        
        # Create object name with user prefix
        object_name = f"users/{x_user_id}/{file.filename}"
        
        # Upload to MinIO
        minio_client.put_object(
            BUCKET_NAME,
            object_name,
            io.BytesIO(content),
            length=file_size,
            content_type=file.content_type or "application/octet-stream"
        )
        
        logger.info(f"File uploaded: {object_name} by user {x_user_id}")
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "object_name": object_name,
            "size": file_size
        }
    
    except S3Error as e:
        logger.error(f"MinIO error: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/files/download/{filename}")
async def download_file(
    filename: str,
    x_user_id: Optional[str] = Header(None)
):
    """Download a file from MinIO storage"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    try:
        object_name = f"users/{x_user_id}/{filename}"
        
        # Get object from MinIO
        response = minio_client.get_object(BUCKET_NAME, object_name)
        
        logger.info(f"File downloaded: {object_name} by user {x_user_id}")
        
        return StreamingResponse(
            response,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found")
        logger.error(f"MinIO error: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/files/list")
async def list_files(x_user_id: Optional[str] = Header(None)):
    """List all files for a user"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    try:
        prefix = f"users/{x_user_id}/"
        objects = minio_client.list_objects(BUCKET_NAME, prefix=prefix, recursive=True)
        
        files = []
        for obj in objects:
            files.append({
                "filename": obj.object_name.split('/')[-1],
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat()
            })
        
        return {"files": files, "count": len(files)}
    
    except S3Error as e:
        logger.error(f"MinIO error: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/files/delete/{filename}")
async def delete_file(
    filename: str,
    x_user_id: Optional[str] = Header(None)
):
    """Delete a file from MinIO storage"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    try:
        object_name = f"users/{x_user_id}/{filename}"
        minio_client.remove_object(BUCKET_NAME, object_name)
        
        logger.info(f"File deleted: {object_name} by user {x_user_id}")
        
        return {"message": "File deleted successfully", "filename": filename}
    
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found")
        logger.error(f"MinIO error: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MinIO connection
        minio_client.bucket_exists(BUCKET_NAME)
        return {"status": "healthy", "storage": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "storage": "disconnected"}