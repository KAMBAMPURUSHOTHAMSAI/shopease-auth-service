import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routers.auth_routes import router as auth_router

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(auth_router)


@app.get("/", tags=["Health"])
def root():
    return {"service": settings.app_name, "version": settings.app_version, "status": "running"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "shopease-auth-service"}


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    """Return a safe generic 500 response without exposing internal details."""
    logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )
