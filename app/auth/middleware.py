from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Request, Response
from app.auth.jwt import decode_token, create_access_token
from jose import JWTError
from app.db.mongo import db

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
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
                user = await db["users"].find_one({"id": user_data["id"], "refresh_token": refresh_token})
                if user:
                    new_access = create_access_token({"id": user["id"], "email": user["email"]})
                    response = await call_next(request)
                    response.set_cookie("access_token", new_access, httponly=True)
                    request.state.user = user
                    return response
            except JWTError:
                pass

        return await call_next(request)
