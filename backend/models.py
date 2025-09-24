"""Data models for the Team Stack Ranking Manager."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# SQLAlchemy Base
Base = declarative_base()


def get_current_snapshot() -> str:
    """Get the current snapshot in YYYYH1 or YYYYH2 format."""
    now = datetime.now()
    year = now.year
    # H1 is first half (Jan-Jun), H2 is second half (Jul-Dec)
    half = "H1" if now.month <= 6 else "H2"
    return f"{year}{half}"


# SQLAlchemy Models for Database
class MemberDB(Base):
    """SQLAlchemy model for team members."""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alias = Column(String(100), unique=True, nullable=False, index=True)
    role = Column(String(50), nullable=False, index=True)

    # Relationships
    scores = relationship("ScoreDB", back_populates="member", cascade="all, delete-orphan")
    expected_rankings = relationship("ExpectedRankingDB", back_populates="member", cascade="all, delete-orphan")


class MetricDB(Base):
    """SQLAlchemy model for metrics."""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    min_value = Column(Float, nullable=False, default=0.0)
    max_value = Column(Float, nullable=False, default=10.0)

    # Relationships
    weights = relationship("MetricWeightDB", back_populates="metric", cascade="all, delete-orphan")
    scores = relationship("ScoreDB", back_populates="metric", cascade="all, delete-orphan")


class MetricWeightDB(Base):
    """SQLAlchemy model for metric weights by role."""
    __tablename__ = "metric_weights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(Integer, ForeignKey("metrics.id"), nullable=False)
    role = Column(String(50), nullable=False, index=True)
    weight = Column(Integer, nullable=False, default=0)  # Weight as integer (0-1000)

    # Relationships
    metric = relationship("MetricDB", back_populates="weights")

    # Constraints
    __table_args__ = (UniqueConstraint('metric_id', 'role', name='_metric_role_weight_uc'),)


class ScoreDB(Base):
    """SQLAlchemy model for individual scores."""
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    metric_id = Column(Integer, ForeignKey("metrics.id"), nullable=False)
    score = Column(Integer, nullable=False, default=0)  # Score as integer (0-10)
    snapshot = Column(String(7), nullable=False, default=get_current_snapshot)  # Format: YYYYH1 or YYYYH2

    # Relationships
    member = relationship("MemberDB", back_populates="scores")
    metric = relationship("MetricDB", back_populates="scores")

    # Constraints
    __table_args__ = (UniqueConstraint('member_id', 'metric_id', 'snapshot', name='_member_metric_snapshot_score_uc'),)


class ExpectedRankingDB(Base):
    """SQLAlchemy model for expected rankings."""
    __tablename__ = "expected_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    rank = Column(Integer, nullable=False)

    # Relationships
    member = relationship("MemberDB", back_populates="expected_rankings")

    # Constraints
    __table_args__ = (UniqueConstraint('member_id', name='_member_expected_ranking_uc'),)


# Pydantic Models (API Models)
class Member(BaseModel):
    """Team member model."""
    alias: str
    role: str


class Metric(BaseModel):
    """Metric model with role weights and bounds."""
    id: str
    name: str
    weights_by_role: Dict[str, float]
    min_value: float
    max_value: float


class Score(BaseModel):
    """Individual score model."""
    member_alias: str
    metric_name: str
    score: int  # 0-10 integer score
    snapshot: Optional[str] = None  # Format: YYYYH1 or YYYYH2, defaults to current if not provided


class RankingEntry(BaseModel):
    """Individual ranking entry."""
    alias: str
    role: str
    weighted_score: float
    rank: int
    expected_rank: Optional[int] = None
    mismatch: bool = False


class ScoreAdjustmentPreview(BaseModel):
    """Preview of score adjustments."""
    proposed: Dict[str, float]
    achieved_weighted_score: float
    hit_clamps: List[str]


class ScoreAdjustmentRequest(BaseModel):
    """Request for score adjustment preview."""
    alias: str
    selected_metrics: List[str]
    percent: float = Field(default=5.0, ge=0.1, le=50.0)


class ScoreAdjustmentApply(BaseModel):
    """Request to apply score changes."""
    alias: str
    changes: Dict[str, float]
    snapshot: Optional[str] = None  # Format: YYYYH1 or YYYYH2, defaults to current if not provided


class PercentileBucket(BaseModel):
    """Percentile bucket with members."""
    pct: int
    by_role: Dict[str, List[Dict[str, Any]]]


class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any]
