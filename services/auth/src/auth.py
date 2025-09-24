import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET = os.environ.get("JWT_SECRET_KEY", "secret-key") # todo
ALG = "HS256"
TOKEN_EXPIRE_MIN = 30

class AuthManager:

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_delta: timedelta = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MIN)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET, algorithm=ALG)
        return encoded_jwt

    def verify_token(self, token: str) -> dict:
        """Raises JWTError"""
        try:
            payload = jwt.decode(token, SECRET, algorithms=[ALG])
            return payload
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise
