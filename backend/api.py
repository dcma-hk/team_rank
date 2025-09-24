"""API endpoints for the Team Stack Ranking Manager."""

import logging
import tempfile
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
import pandas as pd

from backend.models import (
    Member, Metric, RankingEntry, ScoreAdjustmentRequest,
    ScoreAdjustmentApply, ScoreAdjustmentPreview, PercentileBucket, ErrorResponse,
    BulkExpectedRankingUpdate, BulkRoleUpdate
)
from backend.data_manager import DataManager, DataValidationError
from backend.sqlite_data_manager import SQLiteDataManager, SQLiteDataValidationError
from backend.data_manager_factory import get_data_source_info
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
async def get_scores(
    snapshot: Optional[str] = Query(None, description="Snapshot to retrieve scores for (YYYYH1 or YYYYH2)"),
    data_manager: DataManager = Depends(get_data_manager)
) -> Dict[str, Any]:
    """Get all member scores for all metrics, optionally filtered by snapshot."""
    try:
        metrics = data_manager.get_metrics()
        members = data_manager.get_members()

        # Check if data manager supports snapshot parameter
        if hasattr(data_manager, 'get_member_scores') and 'snapshot' in data_manager.get_member_scores.__code__.co_varnames:
            member_scores = data_manager.get_member_scores(snapshot=snapshot)
        else:
            member_scores = data_manager.get_member_scores()

        # Get available snapshots if supported
        available_snapshots = []
        if hasattr(data_manager, 'get_available_snapshots'):
            available_snapshots = data_manager.get_available_snapshots()

        # Get current snapshot if supported
        current_snapshot = None
        if hasattr(data_manager, 'get_current_snapshot'):
            current_snapshot = data_manager.get_current_snapshot()

        return {
            "metrics": [m.name for m in metrics],
            "members": [m.alias for m in members],
            "scores": member_scores,
            "current_snapshot": current_snapshot,
            "available_snapshots": available_snapshots,
            "requested_snapshot": snapshot
        }
    except Exception as e:
        logger.error(f"Error getting scores: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scores")


@router.get("/rankings")
async def get_rankings(
    roles: Optional[str] = Query(None, description="Comma-separated list of roles"),
    snapshot: Optional[str] = Query(None, description="Snapshot to calculate rankings for (YYYYH1 or YYYYH2)"),
    ranking_engine: RankingEngine = Depends(get_ranking_engine)
) -> List[RankingEntry]:
    """Get rankings for specified roles, optionally filtered by snapshot."""
    try:
        role_list = None
        if roles:
            role_list = [r.strip() for r in roles.split(",") if r.strip()]

        # Check if ranking engine supports snapshot parameter
        if hasattr(ranking_engine, 'calculate_rankings') and 'snapshot' in ranking_engine.calculate_rankings.__code__.co_varnames:
            return ranking_engine.calculate_rankings(role_list, snapshot=snapshot)
        else:
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


@router.get("/snapshots")
async def get_snapshots(data_manager: DataManager = Depends(get_data_manager)) -> Dict[str, Any]:
    """Get available snapshots and current snapshot."""
    try:
        available_snapshots = []
        current_snapshot = None

        if hasattr(data_manager, 'get_available_snapshots'):
            available_snapshots = data_manager.get_available_snapshots()

        if hasattr(data_manager, 'get_current_snapshot'):
            current_snapshot = data_manager.get_current_snapshot()

        return {
            "current_snapshot": current_snapshot,
            "available_snapshots": available_snapshots
        }
    except Exception as e:
        logger.error(f"Error getting snapshots: {e}")
        raise HTTPException(status_code=500, detail="Failed to get snapshots")


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
    ranking_engine: RankingEngine = Depends(get_ranking_engine),
    adjustment_engine: AdjustmentEngine = Depends(get_adjustment_engine)
) -> Dict[str, Any]:
    """Apply score changes and save to Excel."""
    try:
        # Validate one-level restriction before applying changes
        is_valid, validation_message = adjustment_engine.validate_one_level_restriction(
            request.alias, request.changes
        )

        if not is_valid:
            logger.warning(f"One-level restriction violated for {request.alias}: {validation_message}")
            raise HTTPException(status_code=400, detail=validation_message)

        # Update member scores with snapshot support
        if hasattr(data_manager, 'update_member_scores') and 'snapshot' in data_manager.update_member_scores.__code__.co_varnames:
            data_manager.update_member_scores(request.alias, request.changes, snapshot=request.snapshot)
        else:
            data_manager.update_member_scores(request.alias, request.changes)

        # Save data
        data_manager.save_data()

        # Get updated rankings with snapshot support
        if hasattr(ranking_engine, 'calculate_rankings') and 'snapshot' in ranking_engine.calculate_rankings.__code__.co_varnames:
            updated_rankings = ranking_engine.calculate_rankings(snapshot=request.snapshot)
        else:
            updated_rankings = ranking_engine.calculate_rankings()

        return {
            "ok": True,
            "updatedAt": "now",  # In a real app, you'd use actual timestamp
            "rankings": updated_rankings,
            "snapshot": request.snapshot
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like validation errors)
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


# Database Management Endpoints
@router.get("/data-source")
async def get_data_source() -> Dict[str, Any]:
    """Get information about the current data source."""
    try:
        return get_data_source_info()
    except Exception as e:
        logger.error(f"Error getting data source info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get data source info")


@router.post("/database/migrate")
async def migrate_to_sqlite(data_manager: DataManager = Depends(get_data_manager)) -> Dict[str, Any]:
    """Migrate data from Excel/CSV to SQLite."""
    try:
        # Check if current data manager is already SQLite
        if isinstance(data_manager, SQLiteDataManager):
            raise HTTPException(status_code=400, detail="Already using SQLite data source")

        # Create SQLite data manager and migrate
        from backend.config import settings
        sqlite_manager = SQLiteDataManager(settings.SQLITE_PATH)
        sqlite_manager.migrate_from_csv(data_manager)

        return {
            "ok": True,
            "message": "Data successfully migrated to SQLite",
            "sqlite_path": settings.SQLITE_PATH
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error migrating to SQLite: {e}")
        raise HTTPException(status_code=500, detail="Failed to migrate data to SQLite")


@router.post("/database/seed")
async def seed_mock_data(data_manager: DataManager = Depends(get_data_manager)) -> Dict[str, Any]:
    """Seed the database with mock data (SQLite only)."""
    try:
        if not isinstance(data_manager, SQLiteDataManager):
            raise HTTPException(status_code=400, detail="Mock data seeding only available for SQLite data source")

        data_manager.seed_mock_data()

        return {
            "ok": True,
            "message": "Mock data successfully seeded",
            "note": "Scores are integers 0-10, weights are integers 0-1000"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error seeding mock data: {e}")
        raise HTTPException(status_code=500, detail="Failed to seed mock data")


@router.post("/upload/excel")
async def upload_excel_data(
    file: UploadFile = File(...),
    snapshot: str = Form(...),
    data_manager: DataManager = Depends(get_data_manager),
    ranking_engine: RankingEngine = Depends(get_ranking_engine)
) -> Dict[str, Any]:
    """Upload Excel file to replace data for a specific snapshot."""
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")

        # Validate snapshot format (YYYYH1 or YYYYH2)
        if not snapshot or len(snapshot) != 6 or not snapshot[:4].isdigit() or snapshot[4:] not in ['H1', 'H2']:
            raise HTTPException(status_code=400, detail="Snapshot must be in format YYYYH1 or YYYYH2 (e.g., 2024H1)")

        # Create temporary file to save uploaded content
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            try:
                # Read and save uploaded file
                content = await file.read()
                temp_file.write(content)
                temp_file.flush()

                # Validate Excel file structure
                try:
                    excel_data = pd.read_excel(temp_file.name, sheet_name=None)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid Excel file format: {str(e)}")

                # Check for required sheets (case insensitive)
                sheet_names = [name.lower() for name in excel_data.keys()]
                required_sheets = ['scores']  # At minimum, we need scores sheet

                if not any('score' in sheet_name for sheet_name in sheet_names):
                    raise HTTPException(
                        status_code=400,
                        detail="Excel file must contain a 'Scores' sheet with metric data"
                    )

                # Find the scores sheet
                scores_sheet_name = None
                for original_name, lower_name in zip(excel_data.keys(), sheet_names):
                    if 'score' in lower_name:
                        scores_sheet_name = original_name
                        break

                if not scores_sheet_name:
                    raise HTTPException(status_code=400, detail="Could not find Scores sheet in Excel file")

                scores_df = excel_data[scores_sheet_name]

                # Validate scores sheet structure
                if scores_df.empty:
                    raise HTTPException(status_code=400, detail="Scores sheet is empty")

                # Check if data manager supports snapshot operations
                if not hasattr(data_manager, 'replace_snapshot_data'):
                    raise HTTPException(
                        status_code=400,
                        detail="Current data source does not support snapshot data replacement"
                    )

                # Replace data for the specified snapshot
                data_manager.replace_snapshot_data(scores_df, snapshot)

                # Save the updated data
                data_manager.save_data()

                # Get updated rankings for the snapshot
                if hasattr(ranking_engine, 'calculate_rankings') and 'snapshot' in ranking_engine.calculate_rankings.__code__.co_varnames:
                    updated_rankings = ranking_engine.calculate_rankings(snapshot=snapshot)
                else:
                    updated_rankings = ranking_engine.calculate_rankings()

                return {
                    "ok": True,
                    "message": f"Excel data successfully uploaded and applied to snapshot {snapshot}",
                    "snapshot": snapshot,
                    "records_processed": len(scores_df),
                    "updated_at": "now"
                }

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass  # Ignore cleanup errors

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading Excel data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload Excel data: {str(e)}")


@router.post("/update/expected-rankings")
async def update_expected_rankings(
    request: BulkExpectedRankingUpdate,
    data_manager: DataManager = Depends(get_data_manager),
    ranking_engine: RankingEngine = Depends(get_ranking_engine)
) -> Dict[str, Any]:
    """Update expected rankings for multiple members."""
    try:
        # Get all members to validate aliases and get roles
        all_members = data_manager.get_members()
        member_lookup = {member.alias: member.role for member in all_members}

        # Validate aliases and convert request to list of dictionaries
        rankings_data = []
        for ranking in request.rankings:
            if ranking.alias not in member_lookup:
                raise ValueError(f"Invalid alias: {ranking.alias}. Alias not found in members table.")

            rankings_data.append({
                "alias": ranking.alias,
                "role": member_lookup[ranking.alias],  # Get role from members table
                "rank": ranking.rank
            })

        # Update expected rankings
        data_manager.update_expected_rankings(rankings_data)

        # Save data
        data_manager.save_data()

        # Get updated rankings
        updated_rankings = ranking_engine.calculate_rankings()

        return {
            "ok": True,
            "message": f"Successfully updated expected rankings for {len(rankings_data)} members",
            "updated_count": len(rankings_data),
            "updated_at": "now"
        }

    except (ValueError, DataValidationError, SQLiteDataValidationError) as e:
        logger.warning(f"Invalid expected rankings update request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating expected rankings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update expected rankings")


@router.post("/update/roles")
async def update_roles(
    request: BulkRoleUpdate,
    data_manager: DataManager = Depends(get_data_manager),
    ranking_engine: RankingEngine = Depends(get_ranking_engine)
) -> Dict[str, Any]:
    """Update roles for multiple members."""
    try:
        # Convert request to list of dictionaries
        roles_data = [
            {
                "alias": role.alias,
                "role": role.role
            }
            for role in request.roles
        ]

        # Update roles
        data_manager.update_roles(roles_data)

        # Save data
        data_manager.save_data()

        # Get updated rankings
        updated_rankings = ranking_engine.calculate_rankings()

        return {
            "ok": True,
            "message": f"Successfully updated roles for {len(roles_data)} members",
            "updated_count": len(roles_data),
            "updated_at": "now"
        }

    except (ValueError, DataValidationError, SQLiteDataValidationError) as e:
        logger.warning(f"Invalid roles update request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to update roles")



