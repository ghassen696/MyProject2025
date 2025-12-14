from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.config import SECRET_KEY, ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: int = 240):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def check_password_strength(password: str) -> list:
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not any(c.isupper() for c in password):
        errors.append("Must contain at least one uppercase letter.")
    if not any(c.islower() for c in password):
        errors.append("Must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        errors.append("Must contain at least one digit.")
    if not any(c in "@$!%*?&" for c in password):
        errors.append("Must contain at least one special character (@$!%*?&).")
    return errors
