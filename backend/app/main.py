from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1 import router
from .database import Base, engine
from . import models  # noqa: F401 - register models before create_all

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="My Wardrobe API",
    description="Local-first wardrobe catalog API, designed for later GPT Actions/MCP adapters.",
    version="0.2.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
)
origins = [origin.strip() for origin in os.getenv("WARDROBE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def keep_wardrobe_data_private(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


app.include_router(router)


@app.get("/", include_in_schema=False)
def root():
    return {"name": "My Wardrobe API", "docs": "/docs", "openapi": "/openapi.json"}
