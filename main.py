"""
Main application entry point for the Alerting & Notification Platform.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.admin_routes import admin_router
from src.api.user_routes import user_router
from src.database.database import init_db
from src.services.reminder_service import ReminderService
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    init_db()
    
    # Start reminder service
    reminder_service = ReminderService()
    reminder_service.start()
    
    yield
    
    # Shutdown
    reminder_service.stop()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Alerting & Notification Platform",
        description="A lightweight alerting system with admin configurability and user control",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(admin_router, prefix="/admin", tags=["Admin"])
    app.include_router(user_router, prefix="/user", tags=["User"])
    
    @app.get("/")
    async def root():
        return {
            "message": "Alerting & Notification Platform API",
            "version": "1.0.0",
            "docs": "/docs"
        }
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )