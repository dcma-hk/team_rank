"""API endpoints for the Team Stack Ranking Manager."""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from backend.models import (
    Member, Metric, RankingEntry, ScoreAdjustmentRequest, 
    ScoreAdjustmentApply, ScoreAdjustmentPreview, PercentileBucket, ErrorResponse
)
from backend.data_manager import DataManager, DataValidationError
from backend.ranking_engine import RankingEngine
from backend.adjustment_engine import AdjustmentEngine

logger = logging.getLogger(__name__)
router = APIRouter()

# Global instances - will be injected by main.py
_data_manager: Optional[DataManager] = None
_ranking_engine: Optional[RankingEngine] = None
_adjustment_engine: Optional[AdjustmentEngine] = None


def get_data_manager() -> DataManager:
    """Dependency to get data manager instance."""
    if _data_manager is None:
        raise HTTPException(status_code=500, detail="Data manager not initialized")
    return _data_manager


def get_ranking_engine() -> RankingEngine:
    """Dependency to get ranking engine instance."""
    if _ranking_engine is None:
        raise HTTPException(status_code=500, detail="Ranking engine not initialized")
    return _ranking_engine


def get_adjustment_engine() -> AdjustmentEngine:
    """Dependency to get adjustment engine instance."""
    if _adjustment_engine is None:
        raise HTTPException(status_code=500, detail="Adjustment engine not initialized")
    return _adjustment_engine


def init_engines(data_manager: DataManager):
    """Initialize engine instances."""
    global _data_manager, _ranking_engine, _adjustment_engine
    _data_manager = data_manager
    _ranking_engine = RankingEngine(data_manager)
    _adjustment_engine = AdjustmentEngine(data_manager, _ranking_engine)





@router.get("/roles")
async def get_roles(data_manager: DataManager = Depends(get_data_manager)) -> Dict[str, Any]:
    """Get all roles and their member counts."""
    try:
        roles = data_manager.get_roles()
        counts_by_role = data_manager.get_role_counts()
        
        return {
            "roles": roles,
            "countsByRole": counts_by_role
        }
    except Exception as e:
        logger.error(f"Error getting roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to get roles")


@router.get("/members")
async def get_members(data_manager: DataManager = Depends(get_data_manager)) -> List[Member]:
    """Get all team members."""
    try:
        return data_manager.get_members()
    except Exception as e:
        logger.error(f"Error getting members: {e}")
        raise HTTPException(status_code=500, detail="Failed to get members")


@router.get("/metrics")
async def get_metrics(data_manager: DataManager = Depends(get_data_manager)) -> List[Metric]:
    """Get all metrics with role weights and bounds."""
    try:
        return data_manager.get_metrics()
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@router.get("/scores")
async def get_scores(data_manager: DataManager = Depends(get_data_manager)) -> Dict[str, Any]:
    """Get all member scores for all metrics."""
    try:
        metrics = data_manager.get_metrics()
        members = data_manager.get_members()
        member_scores = data_manager.get_member_scores()
        
        return {
            "metrics": [m.name for m in metrics],
            "members": [m.alias for m in members],
            "scores": member_scores
        }
    except Exception as e:
        logger.error(f"Error getting scores: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scores")


@router.get("/rankings")
async def get_rankings(
    roles: Optional[str] = Query(None, description="Comma-separated list of roles"),
    ranking_engine: RankingEngine = Depends(get_ranking_engine)
) -> List[RankingEntry]:
    """Get rankings for specified roles."""
    try:
        role_list = None
        if roles:
            role_list = [r.strip() for r in roles.split(",") if r.strip()]
        
        return ranking_engine.calculate_rankings(role_list)
    except Exception as e:
        logger.error(f"Error getting rankings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get rankings")


@router.get("/mismatches")
async def get_mismatches(
    ranking_engine: RankingEngine = Depends(get_ranking_engine)
) -> List[RankingEntry]:
    """Get ordered list of members with rank ≠ expected rank."""
    try:
        return ranking_engine.get_mismatches()
    except Exception as e:
        logger.error(f"Error getting mismatches: {e}")
        raise HTTPException(status_code=500, detail="Failed to get mismatches")


@router.post("/adjust/preview")
async def preview_adjustment(
    request: ScoreAdjustmentRequest,
    adjustment_engine: AdjustmentEngine = Depends(get_adjustment_engine)
) -> ScoreAdjustmentPreview:
    """Preview score adjustments for a member."""
    try:
        return adjustment_engine.preview_adjustment(
            request.alias,
            request.selected_metrics,
            request.percent
        )
    except ValueError as e:
        logger.warning(f"Invalid adjustment request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error previewing adjustment: {e}")
        raise HTTPException(status_code=500, detail="Failed to preview adjustment")


@router.post("/adjust/apply")
async def apply_adjustment(
    request: ScoreAdjustmentApply,
    data_manager: DataManager = Depends(get_data_manager),
    ranking_engine: RankingEngine = Depends(get_ranking_engine)
) -> Dict[str, Any]:
    """Apply score changes and save to Excel."""
    try:
        # Update member scores
        data_manager.update_member_scores(request.alias, request.changes)

        # Save data
        data_manager.save_data()

        # Get updated rankings
        updated_rankings = ranking_engine.calculate_rankings()

        return {
            "ok": True,
            "updatedAt": "now",  # In a real app, you'd use actual timestamp
            "rankings": updated_rankings
        }
    except ValueError as e:
        logger.warning(f"Invalid apply request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error applying adjustment: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply adjustment")


@router.get("/percentiles")
async def get_percentiles(
    basis: str = Query("weighted", regex="^(weighted|rank)$", description="Basis for percentiles: 'weighted' or 'rank'"),
    ranking_engine: RankingEngine = Depends(get_ranking_engine)
) -> Dict[str, List[PercentileBucket]]:
    """Get organizational percentiles by role."""
    try:
        rankings = ranking_engine.calculate_rankings()
        roles = list(set(r.role for r in rankings))

        buckets = []

        for pct in range(10, 101, 10):  # 10%, 20%, ..., 100%
            bucket_data = {}

            for role in roles:
                role_rankings = [r for r in rankings if r.role == role]
                if not role_rankings:
                    bucket_data[role] = []
                    continue

                # Sort by the chosen basis
                if basis == "weighted":
                    role_rankings.sort(key=lambda x: -x.weighted_score)  # Descending
                    # Calculate percentile threshold
                    threshold_idx = int((pct / 100.0) * len(role_rankings)) - 1
                    threshold_idx = max(0, min(threshold_idx, len(role_rankings) - 1))

                    # Get members in this percentile bucket
                    if pct == 10:
                        bucket_members = role_rankings[:threshold_idx + 1]
                    else:
                        prev_threshold_idx = int(((pct - 10) / 100.0) * len(role_rankings)) - 1
                        prev_threshold_idx = max(0, min(prev_threshold_idx, len(role_rankings) - 1))
                        bucket_members = role_rankings[prev_threshold_idx + 1:threshold_idx + 1]
                else:  # basis == "rank"
                    role_rankings.sort(key=lambda x: x.rank)  # Ascending
                    # For rank-based, we use rank ranges
                    max_rank = max(r.rank for r in role_rankings)
                    rank_threshold = int((pct / 100.0) * max_rank)

                    if pct == 10:
                        bucket_members = [r for r in role_rankings if r.rank <= rank_threshold]
                    else:
                        prev_rank_threshold = int(((pct - 10) / 100.0) * max_rank)
                        bucket_members = [r for r in role_rankings if prev_rank_threshold < r.rank <= rank_threshold]

                # Format member data
                member_data = []
                for member in bucket_members:
                    if basis == "weighted":
                        member_data.append({
                            "alias": member.alias,
                            "weightedScore": member.weighted_score
                        })
                    else:
                        member_data.append({
                            "alias": member.alias,
                            "rank": member.rank
                        })

                bucket_data[role] = member_data

            buckets.append(PercentileBucket(pct=pct, by_role=bucket_data))

        return {"buckets": buckets}

    except Exception as e:
        logger.error(f"Error getting percentiles: {e}")
        raise HTTPException(status_code=500, detail="Failed to get percentiles")
