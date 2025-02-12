"""
This module defines the main FastAPI application for Money Manager.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from api.routers import (
    accounts,
    analytics,
    categories,
    expenses,
    exports,
    users,
)
from config.config import API_BIND_HOST, API_BIND_PORT


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan function that handles app startup and shutdown"""
    yield
    # Handles the shutdown event to close the MongoDB client
    await users.shutdown_db_client()


app = FastAPI(
    lifespan=lifespan,
    description="API documentation for Money Manager application",
    version="1.0.0",
    docs_url="/docs",  # Default Swagger UI endpoint
    redoc_url="/redoc",  # Alternative API documentation using ReDoc
    openapi_url="/openapi.json",  # OpenAPI schema JSON file
)


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


# Include routers for different functionalities
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(analytics.router)
app.include_router(exports.router)

if __name__ == "__main__":
    uvicorn.run("app:app", host=API_BIND_HOST, port=API_BIND_PORT, reload=True)
