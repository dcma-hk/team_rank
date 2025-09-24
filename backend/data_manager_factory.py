"""Factory for creating appropriate data manager instances."""

import logging
from typing import Union

from backend.config import settings
from backend.data_manager import DataManager
from backend.sqlite_data_manager import SQLiteDataManager

logger = logging.getLogger(__name__)


def create_data_manager() -> Union[DataManager, SQLiteDataManager]:
    """Create and return the appropriate data manager based on configuration."""
    data_source = settings.DATA_SOURCE.lower()
    
    if data_source == "sqlite":
        logger.info(f"Using SQLite data source: {settings.SQLITE_PATH}")
        return SQLiteDataManager(settings.SQLITE_PATH)
    elif data_source == "excel":
        logger.info(f"Using Excel/CSV data source: {settings.EXCEL_PATH}")
        return DataManager(settings.EXCEL_PATH)
    else:
        logger.warning(f"Unknown data source '{data_source}', defaulting to Excel/CSV")
        return DataManager(settings.EXCEL_PATH)


def get_data_source_info() -> dict:
    """Get information about the current data source configuration."""
    data_source = settings.DATA_SOURCE.lower()
    
    if data_source == "sqlite":
        return {
            "type": "sqlite",
            "path": settings.SQLITE_PATH,
            "description": "SQLite Database"
        }
    else:
        return {
            "type": "excel",
            "path": settings.EXCEL_PATH,
            "description": "Excel/CSV Files"
        }
