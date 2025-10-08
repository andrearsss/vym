from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response, JSONResponse
import httpx
import os
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client: Optional[httpx.AsyncClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # executed at startup
    global client
    client = httpx.AsyncClient(timeout=30.0)
    yield
    # executed before shutdown
    await client.aclose()

app = FastAPI(
    title="Vym API Gateway",
    description="Vym API Gateway",
    version="1.0.0",
    lifespan = lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # todo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

# Service URLs from environment
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8001")
# TELEMETRY_SERVICE_URL = os.getenv("TELEMETRY_SERVICE_URL", "http://telemetry_service:8002")
IMAGE_STORAGE_URL = os.getenv("IMAGE_STORAGE_URL", "http://image-storage:8003")
ML_SERVICE_URL = os.getenv("MLFLOW_SERVICE_URL", "http://mlflow:5000")

# Dependency
async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Validate JWT token with auth service"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/auth/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"}
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        else:
            logger.error(f"Auth service returned status {response.status_code}")
            raise HTTPException(status_code=503, detail="Authentication service error")

    except httpx.RequestError as e:
        logger.error(f"Error connecting to auth service: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable")
    except HTTPException:
        # re-raise exception as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error validating token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def proxy_request(url: str, method: str, request: Request, extra_headers: dict = None, **kwargs):
    """
    Proxy HTTP request to backend service
    
    Args:
        url: Target service URL
        method: HTTP method (GET, POST, etc.)
        request: Original FastAPI request
        extra_headers: Additional headers to add to the request
        **kwargs: Additional arguments to pass to httpx.request
    """
    try:
        body = await request.body() if method.upper() in ["POST", "PUT", "PATCH"] else None

        excluded = {"host", "content-length", "connection"}
        headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded}
        
        # Add extra headers if provided
        if extra_headers:
            headers.update(extra_headers)

        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
            **kwargs
        )

        # Handle different content types
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        elif "image/" in content_type:
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type=content_type,
                headers=dict(response.headers)
            )
        else:
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

    except httpx.RequestError as e:
        logger.error(f"Request error [{method} {url}]: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")
    except Exception as e:
        logger.error(f"Proxy error [{method} {url}]: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    
# Authentication routes
@app.get("/auth/me")
async def get_profile(request: Request):
    url = f"{AUTH_SERVICE_URL}/auth/me"
    return await proxy_request(url, "GET", request)

@app.post("/auth/signup")
async def signup(request: Request):
    url = f"{AUTH_SERVICE_URL}/auth/signup"
    return await proxy_request(url, "POST", request)

@app.post("/auth/login")
async def login(request: Request):
    url = f"{AUTH_SERVICE_URL}/auth/login"
    return await proxy_request(url, "POST", request)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    services = {
        "auth": AUTH_SERVICE_URL,
        #"telemetry": TELEMETRY_SERVICE_URL,
        "image": IMAGE_STORAGE_URL,
        "ml": ML_SERVICE_URL
    }

    status = {"status": "healthy", "services": {}}
    all_healthy = True
    
    for service_name, service_url in services.items():
        try:
            health_endpoints = ["/health"]
            service_status = "unhealthy"
            
            for endpoint in health_endpoints:
                try:
                    response = await client.get(f"{service_url}{endpoint}", timeout=5.0)
                    if response.status_code == 200:
                        service_status = "healthy"
                        break
                except:
                    continue
            
            status["services"][service_name] = service_status
            if service_status == "unhealthy":
                all_healthy = False
                
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            status["services"][service_name] = "unhealthy"
            all_healthy = False
    
    status["status"] = "healthy" if all_healthy else "degraded"
    return status



# Image storage routes
@app.post("/images/upload")
async def upload_image(request: Request, user: dict = Depends(get_current_user)):
    """Upload an image"""
    url = f"{IMAGE_STORAGE_URL}/upload"
    user_id = str(user.get("id") or user.get("user_id"))
    return await proxy_request(url, "POST", request, extra_headers={"X-User-Id": user_id})

@app.get("/images/list") # todo: handle permissions
async def list_images(request: Request, user: dict = Depends(get_current_user)):
    """List user's images"""
    url = f"{IMAGE_STORAGE_URL}/list"
    user_id = str(user.get("id") or user.get("user_id"))
    return await proxy_request(url, "GET", request, extra_headers={"X-User-Id": user_id})

@app.get("/images/{filename}") # todo: use object id, handle permissions
async def get_image(filename: str, request: Request, user: dict = Depends(get_current_user)):
    """Get a specific image"""
    url = f"{IMAGE_STORAGE_URL}/{filename}"
    user_id = str(user.get("id") or user.get("user_id"))
    return await proxy_request(url, "GET", request, extra_headers={"X-User-Id": user_id})

@app.delete("/images/{filename}") # todo: use object id, handle permissions
async def delete_image(filename: str, request: Request, user: dict = Depends(get_current_user)):
    """Delete an image"""
    url = f"{IMAGE_STORAGE_URL}/{filename}"
    user_id = str(user.get("id") or user.get("user_id"))
    return await proxy_request(url, "DELETE", request, extra_headers={"X-User-Id": user_id})


'''


# Telemetry routes
@app.post("/telemetry/events")
async def log_telemetry(request: Request, user=Depends(get_current_user)):
    """Log telemetry events"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    url = f"{TELEMETRY_SERVICE_URL}/telemetry/events"
    return await proxy_request(url, "POST", request)

@app.get("/telemetry/events")
async def get_telemetry(request: Request, user=Depends(get_current_user)):
    """Get telemetry events"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    url = f"{TELEMETRY_SERVICE_URL}/telemetry/events"
    return await proxy_request(url, "GET", request)


@app.get("/images/{image_id}")
async def get_image(image_id: str, request: Request, user=Depends(get_current_user)):
    """Get specific image"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    url = f"{IMAGE_STORAGE_URL}/images/{image_id}"
    return await proxy_request(url, "GET", request)

    


# # ML Training routes
# @app.post("/mlflow/training/start")
# async def start_training(request: Request, user=Depends(get_current_user)):
#     """Start ML training job"""
#     if not user:
#         raise HTTPException(status_code=401, detail="Authentication required")
    
#     url = f"{ML_SERVICE_URL}/ml/training/start"
#     return await proxy_request(url, "POST", request)

# @app.get("/mlflow/training/jobs")
# async def list_training_jobs(request: Request, user=Depends(get_current_user)):
#     """List training jobs"""
#     if not user:
#         raise HTTPException(status_code=401, detail="Authentication required")
    
#     url = f"{ML_SERVICE_URL}/ml/training/jobs"
#     return await proxy_request(url, "GET", request)

# @app.get("/mlflow/training/{job_id}")
# async def get_training_job(job_id: str, request: Request, user=Depends(get_current_user)):
#     """Get training job status"""
#     if not user:
#         raise HTTPException(status_code=401, detail="Authentication required")
    
#     url = f"{ML_SERVICE_URL}/ml/training/{job_id}"
#     return await proxy_request(url, "GET", request)

# @app.get("/mlflow/models")
# async def list_models(request: Request, user=Depends(get_current_user)):
#     """List ML models"""
#     if not user:
#         raise HTTPException(status_code=401, detail="Authentication required")
    
#     url = f"{ML_SERVICE_URL}/ml/models"
#     return await proxy_request(url, "GET", request)

    '''