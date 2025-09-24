import logging
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uvicorn.config import LOGGING_CONFIG
from sqlalchemy.orm import Session
from database import get_db, engine
from models import *
from auth import AuthManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Change 'univcorn.error' logger name
LOGGING_CONFIG['formatters']['default']['fmt'] = '%(name)s %(levelprefix)s %(message)s'
logger = logging.getLogger('uvicorn.error')
logger.name = 'uvicorn'

app = FastAPI(
    title="Authentication Service",
    description="User authentication and authorization service",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)
auth_manager = AuthManager()
security = HTTPBearer()

# Dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Verify token and get user from db"""
    try:
        payload = auth_manager.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth_service"}

@app.post("/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user
        hashed_password = auth_manager.hash_password(user_data.password)
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        token = auth_manager.create_access_token({"sub": str(new_user.id)})

        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=str(new_user.id),
                email=new_user.email,
                username=new_user.username
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

@app.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    try:
        # find by email
        user = db.query(User).filter(User.email == credentials.email).first()
        if not user or not auth_manager.verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # generate token
        token = auth_manager.create_access_token({"sub": str(user.id)})
        
        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                username=user.username
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username
    )