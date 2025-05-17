from fastapi import Depends, HTTPException, status
import jwt
from jwt.exceptions import PyJWTError
# from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from config import settings
# Defines where the token should be retrieved from (e.g., "/login" endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return {"username": username}
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )