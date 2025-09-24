"""SQLite-based data management for the Team Stack Ranking Manager."""

import logging
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path
import random

import pandas as pd
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from backend.models import (
    Base, MemberDB, MetricDB, MetricWeightDB, ScoreDB, ExpectedRankingDB,
    Member, Metric, Score, get_current_snapshot
)
from backend.config import settings

logger = logging.getLogger(__name__)


class SQLiteDataValidationError(Exception):
    """Custom exception for SQLite data validation errors."""
    pass


class SQLiteDataManager:
    """Manages data using SQLite database for the ranking system."""
    
    def __init__(self, db_path: str = "ranking.db"):
        self.db_path = Path(db_path)
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._data_loaded = False
        
        # Thread safety for concurrent data operations
        self._data_lock = threading.RLock()
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        with self._data_lock:
            try:
                Base.metadata.create_all(bind=self.engine)
                self._run_migrations()
                self._data_loaded = True
                logger.info("SQLite database initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                raise SQLiteDataValidationError(f"Database initialization failed: {e}")

    def _run_migrations(self) -> None:
        """Run database migrations."""
        try:
            # Check if snapshot column exists in scores table
            with self.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(scores)"))
                columns = [row[1] for row in result.fetchall()]

                if 'snapshot' not in columns:
                    logger.info("Adding snapshot column to scores table")
                    # Add snapshot column with default value
                    conn.execute(text("ALTER TABLE scores ADD COLUMN snapshot VARCHAR(10) DEFAULT '2024H2'"))
                    # Update existing records with current snapshot
                    from backend.models import get_current_snapshot
                    current_snapshot = get_current_snapshot()
                    conn.execute(text(f"UPDATE scores SET snapshot = '{current_snapshot}' WHERE snapshot IS NULL OR snapshot = '2024H2'"))
                    conn.commit()
                    logger.info("Successfully added snapshot column and updated existing records")
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            # Don't raise here - let the app continue with existing functionality
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def load_data(self) -> None:
        """Load/validate data - for compatibility with existing interface."""
        with self._data_lock:
            if not self._data_loaded:
                self._init_database()
            logger.info("SQLite data validated successfully")
    
    def get_members(self) -> List[Member]:
        """Get all team members."""
        with self._data_lock:
            with self.get_session() as session:
                members_db = session.query(MemberDB).all()
                return [Member(alias=m.alias, role=m.role) for m in members_db]
    
    def get_roles(self) -> List[str]:
        """Get all unique roles."""
        with self._data_lock:
            with self.get_session() as session:
                roles = session.query(MemberDB.role).distinct().all()
                return sorted([role[0] for role in roles])
    
    def get_role_counts(self) -> Dict[str, int]:
        """Get count of members by role."""
        with self._data_lock:
            with self.get_session() as session:
                counts = session.query(
                    MemberDB.role, 
                    func.count(MemberDB.id)
                ).group_by(MemberDB.role).all()
                return {role: count for role, count in counts}
    
    def get_metrics(self) -> List[Metric]:
        """Get all metrics with their role weights and bounds."""
        with self._data_lock:
            with self.get_session() as session:
                metrics_db = session.query(MetricDB).all()
                metrics = []
                
                for metric_db in metrics_db:
                    # Get weights by role
                    weights_by_role = {}
                    for weight_db in metric_db.weights:
                        # Keep integer weight (0-1000) as-is for display
                        weights_by_role[weight_db.role] = float(weight_db.weight)
                    
                    metrics.append(Metric(
                        id=f"M{metric_db.id}",
                        name=metric_db.name,
                        weights_by_role=weights_by_role,
                        min_value=metric_db.min_value,
                        max_value=metric_db.max_value
                    ))
                
                return metrics
    
    def get_member_scores(self, snapshot: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """Get all member scores for all metrics, optionally filtered by snapshot."""
        with self._data_lock:
            with self.get_session() as session:
                query = session.query(ScoreDB).join(MemberDB).join(MetricDB)

                # Filter by snapshot if provided, otherwise use current snapshot
                if snapshot is None:
                    snapshot = get_current_snapshot()
                query = query.filter(ScoreDB.snapshot == snapshot)

                scores_db = query.all()

                member_scores = {}
                for score_db in scores_db:
                    member_alias = score_db.member.alias
                    metric_name = score_db.metric.name
                    # Convert integer score (0-10) to float
                    score_value = float(score_db.score)

                    if member_alias not in member_scores:
                        member_scores[member_alias] = {}
                    member_scores[member_alias][metric_name] = score_value

                return member_scores
    
    def get_expected_rankings(self) -> Dict[str, int]:
        """Get expected rankings for members."""
        with self._data_lock:
            with self.get_session() as session:
                rankings_db = session.query(ExpectedRankingDB).join(MemberDB).all()
                return {ranking.member.alias: ranking.rank for ranking in rankings_db}

    def get_available_snapshots(self) -> List[str]:
        """Get all available snapshots in the database."""
        with self._data_lock:
            with self.get_session() as session:
                snapshots = session.query(ScoreDB.snapshot).distinct().all()
                return sorted([snapshot[0] for snapshot in snapshots], reverse=True)

    def get_current_snapshot(self) -> str:
        """Get the current snapshot identifier."""
        return get_current_snapshot()
    
    def update_member_scores(self, member_alias: str, score_changes: Dict[str, float], snapshot: Optional[str] = None) -> None:
        """Update scores for a specific member in a specific snapshot."""
        with self._data_lock:
            with self.get_session() as session:
                try:
                    # Use current snapshot if not provided
                    if snapshot is None:
                        snapshot = get_current_snapshot()

                    # Get member
                    member = session.query(MemberDB).filter(MemberDB.alias == member_alias).first()
                    if not member:
                        raise SQLiteDataValidationError(f"Member not found: {member_alias}")

                    for metric_name, new_score in score_changes.items():
                        # Get metric
                        metric = session.query(MetricDB).filter(MetricDB.name == metric_name).first()
                        if not metric:
                            raise SQLiteDataValidationError(f"Metric not found: {metric_name}")

                        # Convert float score to integer (0-10)
                        int_score = int(round(new_score))
                        int_score = max(0, min(10, int_score))  # Clamp to 0-10

                        # Update or create score for the specific snapshot
                        score = session.query(ScoreDB).filter(
                            ScoreDB.member_id == member.id,
                            ScoreDB.metric_id == metric.id,
                            ScoreDB.snapshot == snapshot
                        ).first()

                        if score:
                            score.score = int_score
                        else:
                            score = ScoreDB(
                                member_id=member.id,
                                metric_id=metric.id,
                                score=int_score,
                                snapshot=snapshot
                            )
                            session.add(score)

                    session.commit()
                    logger.info(f"Updated scores for member: {member_alias} in snapshot: {snapshot}")

                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to update member scores: {e}")
                    raise SQLiteDataValidationError(f"Score update failed: {e}")
    
    def save_data(self) -> None:
        """Save data - for compatibility with existing interface."""
        # SQLite auto-saves, so this is a no-op
        logger.info("SQLite data is automatically saved")
    
    def is_data_modified(self) -> bool:
        """Check if data has been modified - always return False for SQLite."""
        return False
    
    def start_watching(self) -> None:
        """Start watching - no-op for SQLite."""
        logger.info("File watching not needed for SQLite")
    
    def stop_watching(self) -> None:
        """Stop watching - no-op for SQLite."""
        logger.info("File watching not applicable for SQLite")
    
    @property
    def is_watching(self) -> bool:
        """Check if watching - always False for SQLite."""
        return False

    def migrate_from_csv(self, csv_data_manager) -> None:
        """Migrate data from CSV/Excel data manager to SQLite."""
        with self._data_lock:
            with self.get_session() as session:
                try:
                    # Clear existing data
                    session.query(ScoreDB).delete()
                    session.query(ExpectedRankingDB).delete()
                    session.query(MetricWeightDB).delete()
                    session.query(MetricDB).delete()
                    session.query(MemberDB).delete()

                    # Migrate members
                    csv_members = csv_data_manager.get_members()
                    member_map = {}
                    for member in csv_members:
                        member_db = MemberDB(alias=member.alias, role=member.role)
                        session.add(member_db)
                        session.flush()  # Get the ID
                        member_map[member.alias] = member_db.id

                    # Migrate metrics
                    csv_metrics = csv_data_manager.get_metrics()
                    metric_map = {}
                    for metric in csv_metrics:
                        metric_db = MetricDB(
                            name=metric.name,
                            min_value=metric.min_value,
                            max_value=metric.max_value
                        )
                        session.add(metric_db)
                        session.flush()  # Get the ID
                        metric_map[metric.name] = metric_db.id

                        # Add metric weights
                        for role, weight in metric.weights_by_role.items():
                            # Convert float weight (0.0-1.0) to integer (0-1000)
                            int_weight = int(round(weight * 1000))
                            weight_db = MetricWeightDB(
                                metric_id=metric_db.id,
                                role=role,
                                weight=int_weight
                            )
                            session.add(weight_db)

                    # Migrate scores
                    csv_scores = csv_data_manager.get_member_scores()
                    for member_alias, metric_scores in csv_scores.items():
                        if member_alias not in member_map:
                            continue

                        for metric_name, score_value in metric_scores.items():
                            if metric_name not in metric_map:
                                continue

                            # Convert float score to integer (0-10)
                            int_score = int(round(score_value * 10))  # Assuming CSV scores are 0.0-1.0
                            int_score = max(0, min(10, int_score))

                            score_db = ScoreDB(
                                member_id=member_map[member_alias],
                                metric_id=metric_map[metric_name],
                                score=int_score,
                                snapshot=get_current_snapshot()
                            )
                            session.add(score_db)

                    # Migrate expected rankings
                    csv_expected = csv_data_manager.get_expected_rankings()
                    for member_alias, rank in csv_expected.items():
                        if member_alias not in member_map:
                            continue

                        ranking_db = ExpectedRankingDB(
                            member_id=member_map[member_alias],
                            rank=rank
                        )
                        session.add(ranking_db)

                    session.commit()
                    logger.info("Successfully migrated data from CSV to SQLite")

                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to migrate data: {e}")
                    raise SQLiteDataValidationError(f"Data migration failed: {e}")

    def seed_mock_data(self) -> None:
        """Populate database with mock data using specified ranges."""
        with self._data_lock:
            with self.get_session() as session:
                try:
                    # Clear existing data
                    session.query(ScoreDB).delete()
                    session.query(ExpectedRankingDB).delete()
                    session.query(MetricWeightDB).delete()
                    session.query(MetricDB).delete()
                    session.query(MemberDB).delete()

                    # Create roles and members
                    roles = ["Dev", "PMO", "eTrading", "RISK"]
                    members_per_role = 10

                    member_map = {}
                    for role in roles:
                        for i in range(1, members_per_role + 1):
                            alias = f"{role}{i:02d}"
                            member_db = MemberDB(alias=alias, role=role)
                            session.add(member_db)
                            session.flush()
                            member_map[alias] = member_db.id

                    # Create metrics with role-specific weights
                    metrics_config = [
                        # Dev metrics
                        ("Code Quality", {"Dev": 870, "PMO": 0, "eTrading": 0, "RISK": 0}),
                        ("Velocity", {"Dev": 640, "PMO": 0, "eTrading": 0, "RISK": 0}),
                        ("Architecture", {"Dev": 910, "PMO": 0, "eTrading": 0, "RISK": 0}),
                        ("Testing Coverage", {"Dev": 780, "PMO": 0, "eTrading": 0, "RISK": 0}),
                        ("Incident Response", {"Dev": 550, "PMO": 0, "eTrading": 0, "RISK": 0}),
                        ("Collaboration", {"Dev": 690, "PMO": 0, "eTrading": 0, "RISK": 0}),
                        ("Delivery Predictability", {"Dev": 820, "PMO": 0, "eTrading": 0, "RISK": 0}),

                        # PMO metrics
                        ("Planning Accuracy", {"Dev": 0, "PMO": 880, "eTrading": 0, "RISK": 0}),
                        ("Stakeholder Management", {"Dev": 0, "PMO": 730, "eTrading": 0, "RISK": 0}),
                        ("Resource Allocation", {"Dev": 0, "PMO": 790, "eTrading": 0, "RISK": 0}),
                        ("Timeline Management", {"Dev": 0, "PMO": 850, "eTrading": 0, "RISK": 0}),
                        ("Budget Adherence", {"Dev": 0, "PMO": 710, "eTrading": 0, "RISK": 0}),

                        # eTrading metrics
                        ("Strategy Performance", {"Dev": 0, "PMO": 0, "eTrading": 930, "RISK": 0}),
                        ("Latency Optimization", {"Dev": 0, "PMO": 0, "eTrading": 850, "RISK": 0}),
                        ("Market Coverage", {"Dev": 0, "PMO": 0, "eTrading": 740, "RISK": 0}),
                        ("Risk Controls", {"Dev": 0, "PMO": 0, "eTrading": 680, "RISK": 0}),
                        ("Uptime", {"Dev": 0, "PMO": 0, "eTrading": 800, "RISK": 0}),
                        ("Release Cadence", {"Dev": 0, "PMO": 0, "eTrading": 770, "RISK": 0}),
                        ("Innovation", {"Dev": 0, "PMO": 0, "eTrading": 660, "RISK": 0}),

                        # RISK metrics
                        ("Risk Assessment", {"Dev": 0, "PMO": 0, "eTrading": 0, "RISK": 920}),
                        ("Compliance", {"Dev": 0, "PMO": 0, "eTrading": 0, "RISK": 890}),
                        ("Model Validation", {"Dev": 0, "PMO": 0, "eTrading": 0, "RISK": 760}),
                        ("Reporting Accuracy", {"Dev": 0, "PMO": 0, "eTrading": 0, "RISK": 830}),
                        ("Issue Remediation", {"Dev": 0, "PMO": 0, "eTrading": 0, "RISK": 810}),
                    ]

                    metric_map = {}
                    for metric_name, role_weights in metrics_config:
                        metric_db = MetricDB(
                            name=metric_name,
                            min_value=0.0,
                            max_value=10.0
                        )
                        session.add(metric_db)
                        session.flush()
                        metric_map[metric_name] = metric_db.id

                        # Add weights for each role
                        for role, weight in role_weights.items():
                            weight_db = MetricWeightDB(
                                metric_id=metric_db.id,
                                role=role,
                                weight=weight
                            )
                            session.add(weight_db)

                    # Generate scores (0-10 integers)
                    for member_alias, member_id in member_map.items():
                        # Extract role from member alias (e.g., "Dev01" -> "Dev")
                        member_role = ''.join([c for c in member_alias if not c.isdigit()])
                        if member_role == "ET":
                            member_role = "eTrading"

                        for metric_name, metric_id in metric_map.items():
                            # Generate realistic scores based on role relevance
                            role_weights = dict(metrics_config)[metric_name]
                            if role_weights.get(member_role, 0) > 0:
                                # Higher scores for relevant metrics
                                score = random.randint(3, 10)
                            else:
                                # Lower scores for non-relevant metrics
                                score = random.randint(0, 5)

                            score_db = ScoreDB(
                                member_id=member_id,
                                metric_id=metric_id,
                                score=score,
                                snapshot=get_current_snapshot()
                            )
                            session.add(score_db)

                    # Generate expected rankings (1-10 for each role)
                    for role in roles:
                        role_members = [alias for alias in member_map.keys()
                                      if alias.startswith(role) or
                                      (role == "eTrading" and alias.startswith("ET"))]

                        for i, member_alias in enumerate(sorted(role_members), 1):
                            ranking_db = ExpectedRankingDB(
                                member_id=member_map[member_alias],
                                rank=i
                            )
                            session.add(ranking_db)

                    session.commit()
                    logger.info("Successfully seeded mock data")

                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to seed mock data: {e}")
                    raise SQLiteDataValidationError(f"Mock data seeding failed: {e}")

    def replace_snapshot_data(self, scores_df: pd.DataFrame, snapshot: str) -> None:
        """Replace data for a specific snapshot with uploaded data."""
        with self._data_lock:
            if scores_df.empty:
                raise SQLiteDataValidationError("Uploaded scores data is empty")

            # Check if the first column contains metric names
            if 'metrics' not in scores_df.columns and len(scores_df.columns) > 0:
                # If first column doesn't have a proper name, assume it's metrics
                scores_df = scores_df.copy()
                scores_df.columns = ['metrics'] + list(scores_df.columns[1:])

            # Validate that we have a metrics column
            if 'metrics' not in scores_df.columns:
                raise SQLiteDataValidationError("Uploaded data must have a 'metrics' column")

            with self.get_session() as session:
                try:
                    # Get all metrics and members from the database
                    metrics = {m.name: m.id for m in session.query(MetricDB).all()}
                    members = {m.alias: m.id for m in session.query(MemberDB).all()}

                    # Delete existing scores for this snapshot
                    session.query(ScoreDB).filter(ScoreDB.snapshot == snapshot).delete()

                    # Process the uploaded data
                    processed_count = 0

                    for _, row in scores_df.iterrows():
                        metric_name = row['metrics']

                        # Skip if metric doesn't exist in database
                        if metric_name not in metrics:
                            logger.warning(f"Metric '{metric_name}' not found in database, skipping")
                            continue

                        metric_id = metrics[metric_name]

                        # Process scores for each member
                        for col_name, score_value in row.items():
                            if col_name == 'metrics':
                                continue

                            # Skip role columns and metadata columns
                            if col_name in ['Dev', 'PMO', 'eTrading', 'RISK', 'Max', 'Min']:
                                continue

                            # Skip if member doesn't exist
                            if col_name not in members:
                                continue

                            member_id = members[col_name]

                            # Convert score to float, skip if invalid
                            try:
                                score = float(score_value)
                            except (ValueError, TypeError):
                                continue

                            # Create new score record
                            score_db = ScoreDB(
                                member_id=member_id,
                                metric_id=metric_id,
                                score=score,
                                snapshot=snapshot
                            )
                            session.add(score_db)
                            processed_count += 1

                    session.commit()
                    logger.info(f"Successfully replaced data for snapshot {snapshot} with {processed_count} score records")

                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to replace snapshot data: {e}")
                    raise SQLiteDataValidationError(f"Failed to replace snapshot data: {e}")

    def update_expected_rankings(self, rankings: List[Dict[str, Any]]) -> None:
        """Replace all expected rankings with the provided data."""
        with self._data_lock:
            with self.get_session() as session:
                try:
                    # Validate that all aliases exist in the members table
                    all_aliases = [ranking['alias'] for ranking in rankings]
                    existing_members = session.query(MemberDB.alias).filter(MemberDB.alias.in_(all_aliases)).all()
                    existing_aliases = {member.alias for member in existing_members}
                    invalid_aliases = set(all_aliases) - existing_aliases

                    if invalid_aliases:
                        raise SQLiteDataValidationError(
                            f"Cannot update expected rankings for aliases not found in Roles table: {', '.join(sorted(invalid_aliases))}. "
                            f"Please add these members to the Roles table first."
                        )

                    # Clear all existing expected rankings
                    session.query(ExpectedRankingDB).delete()

                    # Create new expected rankings (no role update needed since role is in members table)
                    for ranking_data in rankings:
                        alias = ranking_data['alias']
                        expected_rank = ranking_data['rank']

                        # Find the member (we know it exists from validation above)
                        member = session.query(MemberDB).filter_by(alias=alias).first()

                        # Create new expected ranking
                        new_ranking = ExpectedRankingDB(member_id=member.id, rank=expected_rank)
                        session.add(new_ranking)

                    session.commit()
                    logger.info(f"Successfully replaced expected rankings for {len(rankings)} members")

                except SQLiteDataValidationError:
                    session.rollback()
                    raise
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to update expected rankings: {e}")
                    raise SQLiteDataValidationError(f"Failed to update expected rankings: {e}")

    def update_roles(self, roles: List[Dict[str, Any]]) -> None:
        """Replace all members with the provided role data."""
        with self._data_lock:
            with self.get_session() as session:
                try:
                    # Validate input data
                    for role_data in roles:
                        if not role_data.get('alias') or not role_data.get('role'):
                            raise SQLiteDataValidationError("Both alias and role must be provided for each member")

                    # Clear all existing members and their related data
                    # This will cascade delete scores and expected rankings due to foreign key constraints
                    session.query(MemberDB).delete()

                    # Create new members with the provided data
                    for role_data in roles:
                        alias = role_data['alias']
                        role = role_data['role']

                        member = MemberDB(alias=alias, role=role)
                        session.add(member)

                    session.commit()
                    logger.info(f"Successfully replaced all members with {len(roles)} new entries")

                except SQLiteDataValidationError:
                    session.rollback()
                    raise
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to update roles: {e}")
                    raise SQLiteDataValidationError(f"Failed to update roles: {e}")


