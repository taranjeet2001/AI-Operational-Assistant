from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.chat_routes import router as chat_router
from app.api.knowledge_routes import router as knowledge_router
from app.api.ticket_routes import router as ticket_router
from app.database.database import create_database_tables
from app.logging_config import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    create_database_tables()
    yield


app = FastAPI(
    title="AI Operations Assistant",
    version="1.0.0",
    description="Agentic internal IT support assistant with knowledge search and ticket tools.",
    lifespan=lifespan,
)
app.include_router(chat_router)
app.include_router(ticket_router)
app.include_router(knowledge_router)

web_directory = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=web_directory), name="static")


@app.get("/", include_in_schema=False)
def chat_page() -> FileResponse:
    return FileResponse(web_directory / "index.html")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
