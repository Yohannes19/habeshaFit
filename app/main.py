from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.routes.web import router as web_router

app = FastAPI(
    title="HabeshaFit",
    description="Event-based outfit ordering platform for the Ethiopian diaspora",
    version="0.1.0",
    docs_url="/docs" if settings.is_dev else None,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
