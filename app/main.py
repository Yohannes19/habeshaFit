from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes.web import router as web_router
from app.api.auth import router as auth_router
from app.db.database import init_db, close_db

app = FastAPI(
    title="HabeshaFit",
    description="Event-based outfit ordering platform for the Ethiopian diaspora",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web_router)
app.include_router(auth_router)


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()


@app.on_event("shutdown")
async def shutdown():
    """Close database connections on shutdown"""
    await close_db()


@app.get("/health")
async def health():
    return {"status": "ok"}
