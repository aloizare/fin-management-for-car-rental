import json
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.db import models
from app.db.database import engine
from app.routers import auth, organization, transaction

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fin-Management API", version="1.0.0")

class StandardResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])

        if 200 <= response.status_code < 300:
            try:
                data = json.loads(body)
                wrapped = {
                    "success": True,
                    "server_message": "OK",
                    **(data if isinstance(data, dict) else {"data": data}),
                }
                return JSONResponse(content=wrapped, status_code=response.status_code)
            except Exception:
                pass

        return StarletteResponse(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
        )


app.add_middleware(StandardResponseMiddleware)


@app.exception_handler(Exception)
async def http_exception_handler(request: Request, exc):
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "server_message": exc.detail},
            headers=exc.headers,
        )
    return JSONResponse(
        status_code=500,
        content={"success": False, "server_message": "Internal server error"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    raw_msg = errors[0]["msg"] if errors else "Validasi gagal"
    message = raw_msg.replace("Value error, ", "")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "server_message": message},
    )

app.include_router(auth.router)
app.include_router(organization.router)
app.include_router(transaction.router)

@app.get("/")
def read_root():
    return {"test"}
