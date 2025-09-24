"""File system watcher for automatic data reloading."""

import logging
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Set

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

if TYPE_CHECKING:
    from backend.data_manager import DataManager

logger = logging.getLogger(__name__)


class DataFileEventHandler(FileSystemEventHandler):
    """Event handler for data file changes."""
    
    def __init__(self, file_watcher: 'DataFileWatcher'):
        super().__init__()
        self.file_watcher = file_watcher
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory:
            self.file_watcher._on_file_changed(event.src_path)
    
    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events (e.g., Excel temp file operations)."""
        if not event.is_directory:
            # Excel often saves by creating temp file and moving it
            self.file_watcher._on_file_changed(event.dest_path)


class DataFileWatcher:
    """Watches data files for changes and triggers automatic reloading."""
    
    def __init__(self, data_manager: 'DataManager', debounce_seconds: float = 2.0):
        """
        Initialize the file watcher.
        
        Args:
            data_manager: The DataManager instance to reload data on changes
            debounce_seconds: Delay before reloading to avoid multiple rapid reloads
        """
        self.data_manager = data_manager
        self.debounce_seconds = debounce_seconds
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[DataFileEventHandler] = None
        
        # Debouncing mechanism
        self._debounce_timer: Optional[threading.Timer] = None
        self._debounce_lock = threading.Lock()
        
        # Track files being watched
        self._watched_files: Set[str] = set()
        
        # Control flags
        self._is_watching = False
        self._is_stopping = False
    
    def start_watching(self) -> None:
        """Start watching data files for changes."""
        if self._is_watching:
            logger.warning("File watcher is already running")
            return
        
        try:
            self.observer = Observer()
            self.event_handler = DataFileEventHandler(self)
            
            # Watch the Excel file if it exists
            excel_path = self.data_manager.excel_path
            if excel_path.exists():
                watch_dir = excel_path.parent
                self.observer.schedule(self.event_handler, str(watch_dir), recursive=False)
                self._watched_files.add(str(excel_path))
                logger.info(f"Watching Excel file: {excel_path}")
            
            # Watch CSV files
            csv_files = ['Roles.csv', 'Scores.csv', 'ExpectedRanking.csv']
            current_dir = Path.cwd()
            
            for csv_file in csv_files:
                csv_path = current_dir / csv_file
                if csv_path.exists():
                    # Only add directory watch if not already watching current directory
                    if str(current_dir) not in [str(Path(f).parent) for f in self._watched_files]:
                        self.observer.schedule(self.event_handler, str(current_dir), recursive=False)
                    self._watched_files.add(str(csv_path))
                    logger.info(f"Watching CSV file: {csv_path}")
            
            if not self._watched_files:
                logger.warning("No data files found to watch")
                return
            
            self.observer.start()
            self._is_watching = True
            logger.info("File watcher started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            self._cleanup()
            raise
    
    def stop_watching(self) -> None:
        """Stop watching files and cleanup resources."""
        if not self._is_watching:
            return
        
        self._is_stopping = True
        logger.info("Stopping file watcher...")
        
        # Cancel any pending debounced reload
        with self._debounce_lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None
        
        self._cleanup()
        logger.info("File watcher stopped")
    
    def _cleanup(self) -> None:
        """Clean up observer and reset state."""
        if self.observer:
            try:
                if self.observer.is_alive():
                    self.observer.stop()
                    self.observer.join(timeout=5.0)
            except Exception as e:
                logger.error(f"Error stopping observer: {e}")
            finally:
                self.observer = None
        
        self.event_handler = None
        self._watched_files.clear()
        self._is_watching = False
        self._is_stopping = False
    
    def _on_file_changed(self, file_path: str) -> None:
        """Handle file change events with debouncing."""
        if self._is_stopping:
            return
        
        # Check if this is a file we care about
        file_path_obj = Path(file_path)
        
        # Check if it's our Excel file
        if file_path_obj.resolve() == self.data_manager.excel_path.resolve():
            logger.debug(f"Excel file changed: {file_path}")
            self._schedule_debounced_reload()
            return
        
        # Check if it's one of our CSV files
        csv_files = {'Roles.csv', 'Scores.csv', 'ExpectedRanking.csv'}
        if file_path_obj.name in csv_files:
            logger.debug(f"CSV file changed: {file_path}")
            self._schedule_debounced_reload()
            return
        
        # Ignore other files (temp files, etc.)
        logger.debug(f"Ignoring file change: {file_path}")
    
    def _schedule_debounced_reload(self) -> None:
        """Schedule a debounced data reload."""
        with self._debounce_lock:
            # Cancel existing timer if any
            if self._debounce_timer:
                self._debounce_timer.cancel()
            
            # Schedule new reload
            self._debounce_timer = threading.Timer(
                self.debounce_seconds, 
                self._reload_data
            )
            self._debounce_timer.start()
            logger.debug(f"Scheduled data reload in {self.debounce_seconds} seconds")
    
    def _reload_data(self) -> None:
        """Reload data from files."""
        if self._is_stopping:
            return
        
        try:
            logger.info("Reloading data due to file changes...")
            self.data_manager.load_data()
            logger.info("Data reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload data: {e}")
            # Don't raise - keep serving old data rather than crashing
        
        finally:
            # Clear the timer reference
            with self._debounce_lock:
                self._debounce_timer = None
    
    @property
    def is_watching(self) -> bool:
        """Check if the watcher is currently active."""
        return self._is_watching
    
    def get_watched_files(self) -> Set[str]:
        """Get the set of files currently being watched."""
        return self._watched_files.copy()
