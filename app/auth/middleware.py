from bson import ObjectId
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Request, Response
from app.auth.jwt import decode_token, create_access_token
from jose import JWTError

from app.db.mongo import get_db


EXCLUDED_PATHS = ["/health", "/docs", "/openapi.json","/auth/login","/auth/register"]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        db = get_db()
        path = request.url.path

        if path in EXCLUDED_PATHS:
            return await call_next(request)
        access_token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")
        
        if access_token:
            try:
                user_data = decode_token(access_token)
                request.state.user = user_data
            except JWTError:
                access_token = None

        if not access_token and refresh_token:
            try:
                user_data = decode_token(refresh_token)
                user = await db["users"].find_one(
                    {"_id": ObjectId(user_data["id"])},
                    {"_id": 1, "email": 1}
                )
                if user:
                    user["id"] = str(user.pop("_id")) 
                    new_access = create_access_token({"id": user["id"], "email": user["email"]})
                    request.state.user = user
                    response = await call_next(request)
                    response.set_cookie("access_token", new_access, httponly=True)
                    return response
            except JWTError:
                pass

        return await call_next(request)
