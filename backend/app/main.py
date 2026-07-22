from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import close_db, init_db
from app.routers import activities, auc, auth, clients, import_data, map, rankings, trading


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Tiger Brokers NZ - Growth Analytics API",
    description="数据分析看板后端 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(clients.router, prefix="/api")
app.include_router(trading.router, prefix="/api")
app.include_router(auc.router, prefix="/api")
app.include_router(rankings.router, prefix="/api")
app.include_router(map.router, prefix="/api")
app.include_router(activities.router, prefix="/api")
app.include_router(import_data.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "growth-analytics-api"}
