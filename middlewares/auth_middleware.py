from fastapi import Depends, HTTPException, status, WebSocket
import jwt
from jwt.exceptions import PyJWTError
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


async def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return {"username": username}
    except PyJWTError:
        return None


async def get_current_websocket_user(websocket: WebSocket) -> dict:
    """Authenticate WebSocket connections using token from query parameters"""
    try:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
            
        user = await verify_token(token)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
            
        return user
        
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None