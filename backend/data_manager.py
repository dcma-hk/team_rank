"""Data management for Excel/CSV files and core data operations."""

import logging
import os
import pandas as pd
import threading
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import fcntl
from contextlib import contextmanager

from backend.models import Member, Metric, RankingEntry
from backend.config import settings

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Custom exception for data validation errors."""
    pass


class DataManager:
    """Manages data loading, validation, and persistence for the ranking system."""
    
    def __init__(self, excel_path: str):
        self.excel_path = Path(excel_path)
        self.roles_df: Optional[pd.DataFrame] = None
        self.scores_df: Optional[pd.DataFrame] = None
        self.expected_ranking_df: Optional[pd.DataFrame] = None
        self._data_loaded = False
        self._last_modified = None

        # Thread safety for concurrent data operations
        self._data_lock = threading.RLock()
        self._file_watcher = None
    
    def load_data(self) -> None:
        """Load data from Excel file or CSV fallbacks."""
        with self._data_lock:
            try:
                if self.excel_path.exists() and self.excel_path.suffix == '.xlsx':
                    self._load_from_excel()
                else:
                    self._load_from_csv()

                self._validate_data()
                self._normalize_data()
                self._data_loaded = True
                self._last_modified = self.excel_path.stat().st_mtime if self.excel_path.exists() else None
                logger.info("Data loaded and validated successfully")

            except Exception as e:
                logger.error(f"Failed to load data: {e}")
                raise DataValidationError(f"Data loading failed: {e}")
    
    def _load_from_excel(self) -> None:
        """Load data from Excel file."""
        logger.info(f"Loading data from Excel file: {self.excel_path}")
        
        try:
            # Read all sheets
            excel_data = pd.read_excel(self.excel_path, sheet_name=None)
            
            # Map sheet names (case insensitive)
            sheet_mapping = {}
            for sheet_name in excel_data.keys():
                lower_name = sheet_name.lower()
                if 'role' in lower_name:
                    sheet_mapping['roles'] = sheet_name
                elif 'score' in lower_name:
                    sheet_mapping['scores'] = sheet_name
                elif 'expected' in lower_name or 'ranking' in lower_name:
                    sheet_mapping['expected'] = sheet_name
            
            # Load dataframes
            if 'roles' in sheet_mapping:
                self.roles_df = excel_data[sheet_mapping['roles']]
            if 'scores' in sheet_mapping:
                self.scores_df = excel_data[sheet_mapping['scores']]
            if 'expected' in sheet_mapping:
                self.expected_ranking_df = excel_data[sheet_mapping['expected']]
                
        except Exception as e:
            logger.warning(f"Failed to load from Excel: {e}. Trying CSV fallback.")
            self._load_from_csv()
    
    def _load_from_csv(self) -> None:
        """Load data from CSV files."""
        logger.info("Loading data from CSV files")
        
        csv_files = {
            'roles': 'Roles.csv',
            'scores': 'Scores.csv', 
            'expected': 'ExpectedRanking.csv'
        }
        
        for key, filename in csv_files.items():
            filepath = Path(filename)
            if filepath.exists():
                df = pd.read_csv(filepath)
                setattr(self, f"{key}_df", df)
                logger.info(f"Loaded {filename}")
            else:
                logger.warning(f"CSV file not found: {filename}")
    
    def _validate_data(self) -> None:
        """Validate loaded data structure and content."""
        errors = []
        
        # Check if required dataframes are loaded
        if self.roles_df is None:
            errors.append("Roles data not found")
        if self.scores_df is None:
            errors.append("Scores data not found")
        if self.expected_ranking_df is None:
            logger.warning("Expected ranking data not found - will proceed without it")
        
        if errors:
            raise DataValidationError(f"Missing required data: {', '.join(errors)}")
        
        # Validate Roles sheet
        required_roles_cols = ['alias', 'role']
        if not all(col in self.roles_df.columns for col in required_roles_cols):
            errors.append(f"Roles sheet missing required columns: {required_roles_cols}")
        
        # Validate Scores sheet structure
        if 'metrics' not in self.scores_df.columns:
            errors.append("Scores sheet missing 'metrics' column")
        
        # Check for reasonable data sizes
        if len(self.roles_df) > settings.MAX_MEMBERS:
            errors.append(f"Too many members: {len(self.roles_df)} > {settings.MAX_MEMBERS}")
        
        if len(self.scores_df) > settings.MAX_METRICS:
            errors.append(f"Too many metrics: {len(self.scores_df)} > {settings.MAX_METRICS}")
        
        if errors:
            raise DataValidationError(f"Data validation failed: {', '.join(errors)}")
    
    def _normalize_data(self) -> None:
        """Normalize and clean data."""
        # Normalize alias and role names (trim whitespace, consistent casing)
        if self.roles_df is not None:
            self.roles_df['alias'] = self.roles_df['alias'].astype(str).str.strip()
            self.roles_df['role'] = self.roles_df['role'].astype(str).str.strip()
            # Remove empty rows
            self.roles_df = self.roles_df.dropna(subset=['alias', 'role'])
            self.roles_df = self.roles_df[self.roles_df['alias'] != '']
        
        if self.scores_df is not None:
            self.scores_df['metrics'] = self.scores_df['metrics'].astype(str).str.strip()
            # Remove empty rows
            self.scores_df = self.scores_df.dropna(subset=['metrics'])
            self.scores_df = self.scores_df[self.scores_df['metrics'] != '']
        
        if self.expected_ranking_df is not None:
            self.expected_ranking_df['alias'] = self.expected_ranking_df['alias'].astype(str).str.strip()
            self.expected_ranking_df['role'] = self.expected_ranking_df['role'].astype(str).str.strip()
            # Remove empty rows
            self.expected_ranking_df = self.expected_ranking_df.dropna(subset=['alias', 'role'])
            self.expected_ranking_df = self.expected_ranking_df[self.expected_ranking_df['alias'] != '']
    
    @contextmanager
    def _file_lock(self):
        """Context manager for file locking during writes."""
        if not self.excel_path.exists():
            yield
            return
            
        with open(self.excel_path, 'r+b') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield
            except IOError:
                raise DataValidationError("File is locked by another process")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def get_members(self) -> List[Member]:
        """Get all team members."""
        with self._data_lock:
            if not self._data_loaded:
                raise DataValidationError("Data not loaded")

            return self._get_members_unsafe()

    def _get_members_unsafe(self) -> List[Member]:
        """Get all team members without locking (for internal use)."""
        members = []
        for _, row in self.roles_df.iterrows():
            members.append(Member(alias=row['alias'], role=row['role']))
        return members
    
    def get_roles(self) -> List[str]:
        """Get all unique roles."""
        with self._data_lock:
            if not self._data_loaded:
                raise DataValidationError("Data not loaded")

            return self._get_roles_unsafe()

    def _get_roles_unsafe(self) -> List[str]:
        """Get all unique roles without locking (for internal use)."""
        return sorted(self.roles_df['role'].unique().tolist())
    
    def get_role_counts(self) -> Dict[str, int]:
        """Get count of members by role."""
        with self._data_lock:
            if not self._data_loaded:
                raise DataValidationError("Data not loaded")

            return self.roles_df['role'].value_counts().to_dict()
    
    def is_data_modified(self) -> bool:
        """Check if the data file has been modified externally."""
        if not self.excel_path.exists():
            return False

        current_mtime = self.excel_path.stat().st_mtime
        return current_mtime != self._last_modified

    def get_metrics(self) -> List[Metric]:
        """Get all metrics with their role weights and bounds."""
        with self._data_lock:
            if not self._data_loaded:
                raise DataValidationError("Data not loaded")

            metrics = []
            roles = self._get_roles_unsafe()  # Already inside lock

            for _, row in self.scores_df.iterrows():
                metric_name = row['metrics']

                # Extract role weights
                weights_by_role = {}
                for role in roles:
                    if role in row:
                        weights_by_role[role] = float(row[role])
                    else:
                        weights_by_role[role] = 0.0

                # Get min/max values
                min_val = float(row.get('Min', 0.0))
                max_val = float(row.get('Max', 1.0))

                # Create metric ID (M1, M2, etc.)
                metric_id = f"M{len(metrics) + 1}"

                metrics.append(Metric(
                    id=metric_id,
                    name=metric_name,
                    weights_by_role=weights_by_role,
                    min_value=min_val,
                    max_value=max_val
                ))

            return metrics

    def get_member_scores(self) -> Dict[str, Dict[str, float]]:
        """Get all member scores for all metrics."""
        with self._data_lock:
            if not self._data_loaded:
                raise DataValidationError("Data not loaded")

            member_scores = {}
            members = [m.alias for m in self._get_members_unsafe()]  # Already inside lock

            for _, row in self.scores_df.iterrows():
                metric_name = row['metrics']

                for member in members:
                    if member in row:
                        if member not in member_scores:
                            member_scores[member] = {}
                        member_scores[member][metric_name] = float(row[member])

            return member_scores

    def get_expected_rankings(self) -> Dict[str, int]:
        """Get expected rankings for members."""
        with self._data_lock:
            if not self._data_loaded or self.expected_ranking_df is None:
                return {}

            expected = {}
            for _, row in self.expected_ranking_df.iterrows():
                alias = row['alias']
                rank = int(row['rank'])
                expected[alias] = rank

            return expected

    def update_member_scores(self, member_alias: str, score_changes: Dict[str, float]) -> None:
        """Update scores for a specific member."""
        with self._data_lock:
            if not self._data_loaded:
                raise DataValidationError("Data not loaded")

            # Update the scores dataframe
            for metric_name, new_score in score_changes.items():
                # Find the metric row
                metric_mask = self.scores_df['metrics'] == metric_name
                if not metric_mask.any():
                    raise DataValidationError(f"Metric not found: {metric_name}")

                # Update the member's score
                if member_alias not in self.scores_df.columns:
                    raise DataValidationError(f"Member not found: {member_alias}")

                self.scores_df.loc[metric_mask, member_alias] = new_score

            # Recompute min/max for affected metrics
            self._recompute_min_max(list(score_changes.keys()))

    def _recompute_min_max(self, metric_names: List[str]) -> None:
        """Recompute min/max values for specified metrics."""
        members = [m.alias for m in self.get_members()]

        for metric_name in metric_names:
            metric_mask = self.scores_df['metrics'] == metric_name
            if not metric_mask.any():
                continue

            # Get all member scores for this metric
            member_scores = []
            for member in members:
                if member in self.scores_df.columns:
                    score = self.scores_df.loc[metric_mask, member].iloc[0]
                    if pd.notna(score):
                        member_scores.append(float(score))

            if member_scores:
                new_min = min(member_scores)
                new_max = max(member_scores)

                # Update min/max in dataframe
                self.scores_df.loc[metric_mask, 'Min'] = new_min
                self.scores_df.loc[metric_mask, 'Max'] = new_max

    def save_data(self) -> None:
        """Save data back to Excel file."""
        with self._data_lock:
            if not self._data_loaded:
                raise DataValidationError("Data not loaded")

            try:
                with self._file_lock():
                    # Check if file was modified externally
                    if self.is_data_modified():
                        logger.warning("File was modified externally. Consider reloading data.")

                    if self.excel_path.suffix == '.xlsx':
                        self._save_to_excel()
                    else:
                        self._save_to_csv()

                    # Update last modified time
                    self._last_modified = self.excel_path.stat().st_mtime if self.excel_path.exists() else None
                    logger.info("Data saved successfully")

            except Exception as e:
                logger.error(f"Failed to save data: {e}")
                raise DataValidationError(f"Data saving failed: {e}")

    def _save_to_excel(self) -> None:
        """Save data to Excel file."""
        with pd.ExcelWriter(self.excel_path, engine='openpyxl') as writer:
            if self.roles_df is not None:
                self.roles_df.to_excel(writer, sheet_name='Roles', index=False)
            if self.scores_df is not None:
                self.scores_df.to_excel(writer, sheet_name='Scores', index=False)
            if self.expected_ranking_df is not None:
                self.expected_ranking_df.to_excel(writer, sheet_name='ExpectedRanking', index=False)

    def _save_to_csv(self) -> None:
        """Save data to CSV files."""
        if self.roles_df is not None:
            self.roles_df.to_csv('Roles.csv', index=False)
        if self.scores_df is not None:
            self.scores_df.to_csv('Scores.csv', index=False)
        if self.expected_ranking_df is not None:
            self.expected_ranking_df.to_csv('ExpectedRanking.csv', index=False)

    def start_watching(self) -> None:
        """Start watching data files for automatic reloading."""
        if self._file_watcher is not None:
            logger.warning("File watcher is already running")
            return

        try:
            from backend.file_watcher import DataFileWatcher
            self._file_watcher = DataFileWatcher(self)
            self._file_watcher.start_watching()
            logger.info("Started file watching for automatic data reloading")
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            self._file_watcher = None
            raise

    def stop_watching(self) -> None:
        """Stop watching data files."""
        if self._file_watcher is not None:
            try:
                self._file_watcher.stop_watching()
                logger.info("Stopped file watching")
            except Exception as e:
                logger.error(f"Error stopping file watcher: {e}")
            finally:
                self._file_watcher = None

    @property
    def is_watching(self) -> bool:
        """Check if file watching is active."""
        return self._file_watcher is not None and self._file_watcher.is_watching

    def replace_snapshot_data(self, scores_df: pd.DataFrame, snapshot: str) -> None:
        """Replace data for a specific snapshot with uploaded data.

        For Excel/CSV data manager, this replaces the entire scores data
        since snapshots are not directly supported in this format.
        """
        with self._data_lock:
            if not self._data_loaded:
                raise DataValidationError("Data not loaded")

            # Validate the uploaded scores DataFrame
            if scores_df.empty:
                raise DataValidationError("Uploaded scores data is empty")

            # Check if the first column contains metric names
            if 'metrics' not in scores_df.columns and len(scores_df.columns) > 0:
                # If first column doesn't have a proper name, assume it's metrics
                scores_df = scores_df.copy()
                scores_df.columns = ['metrics'] + list(scores_df.columns[1:])

            # Validate that we have a metrics column
            if 'metrics' not in scores_df.columns:
                raise DataValidationError("Uploaded data must have a 'metrics' column")

            # Backup current data
            backup_scores_df = self.scores_df.copy() if self.scores_df is not None else None

            try:
                # Replace the scores data
                self.scores_df = scores_df.copy()

                # Validate the new data
                self._validate_data()
                self._normalize_data()

                logger.info(f"Successfully replaced data for snapshot {snapshot} with {len(scores_df)} records")

            except Exception as e:
                # Restore backup on error
                if backup_scores_df is not None:
                    self.scores_df = backup_scores_df
                logger.error(f"Failed to replace snapshot data: {e}")
                raise DataValidationError(f"Failed to replace snapshot data: {e}")
