"""GEOlyze API -- FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routes import analysis, health

app = FastAPI(
    title="GEOlyze API",
    version="1.0.0",
    description="GEO data analysis platform: download, analyse, and visualise GEO datasets.",
)

# -- CORS --
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Routers --
app.include_router(health.router, tags=["health"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
