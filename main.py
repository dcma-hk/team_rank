"""Main FastAPI application for Team Stack Ranking Manager."""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from backend.config import settings
from backend.data_manager import DataValidationError
from backend.sqlite_data_manager import SQLiteDataValidationError
from backend.data_manager_factory import create_data_manager, get_data_source_info
from backend.api import router, init_engines

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global data manager instance
data_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global data_manager
    try:
        logger.info("Starting Team Stack Ranking Manager...")

        # Get data source info and log it
        data_source_info = get_data_source_info()
        logger.info(f"Using data source: {data_source_info['description']} ({data_source_info['path']})")

        # Create appropriate data manager
        data_manager = create_data_manager()
        data_manager.load_data()
        init_engines(data_manager)

        # Start file watching for automatic data reloading (only for Excel/CSV)
        try:
            data_manager.start_watching()
        except Exception as e:
            logger.warning(f"Failed to start file watching: {e}. Continuing without auto-reload.")

        logger.info("Data loaded and engines initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        logger.info("Shutting down Team Stack Ranking Manager...")
        if data_manager is not None:
            try:
                data_manager.stop_watching()
            except Exception as e:
                logger.error(f"Error stopping file watcher: {e}")


app = FastAPI(
    title="Team Stack Ranking Manager",
    description="A web application for managers to view, compare, and adjust team member rankings",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.exception_handler(DataValidationError)
async def data_validation_exception_handler(request, exc):
    """Handle data validation errors."""
    logger.error(f"Data validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "DATA_VALIDATION_ERROR", "message": str(exc)}}
    )


@app.exception_handler(SQLiteDataValidationError)
async def sqlite_data_validation_exception_handler(request, exc):
    """Handle SQLite data validation errors."""
    logger.error(f"SQLite data validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "SQLITE_DATA_VALIDATION_ERROR", "message": str(exc)}}
    )


@app.exception_handler(ValueError)
async def value_error_exception_handler(request, exc):
    """Handle value errors."""
    logger.error(f"Value error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "INVALID_INPUT", "message": str(exc)}}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred"}}
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Team Stack Ranking Manager API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "data_loaded": data_manager is not None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
