"""Data models for the Team Stack Ranking Manager."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


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


class PercentileBucket(BaseModel):
    """Percentile bucket with members."""
    pct: int
    by_role: Dict[str, List[Dict[str, Any]]]


class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any]
