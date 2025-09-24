"""Auto-adjustment algorithm for score modifications."""

import logging
from typing import Dict, List, Tuple, Optional
import math

from backend.models import ScoreAdjustmentPreview, Metric
from backend.data_manager import DataManager
from backend.ranking_engine import RankingEngine
from backend.config import settings

logger = logging.getLogger(__name__)


class AdjustmentEngine:
    """Handles automatic score adjustments with proportional distribution and clamping."""
    
    def __init__(self, data_manager: DataManager, ranking_engine: RankingEngine):
        self.data_manager = data_manager
        self.ranking_engine = ranking_engine
    
    def preview_adjustment(self, member_alias: str, selected_metrics: List[str], 
                         target_percent: float) -> ScoreAdjustmentPreview:
        """Preview score adjustments to achieve target weighted score change."""
        
        # Get member info
        members = self.data_manager.get_members()
        member = next((m for m in members if m.alias == member_alias), None)
        if not member:
            raise ValueError(f"Member not found: {member_alias}")
        
        # Get current rankings to find reference member
        current_rankings = self.ranking_engine.calculate_rankings([member.role])
        current_entry = next((r for r in current_rankings if r.alias == member_alias), None)
        if not current_entry:
            raise ValueError(f"Current ranking not found for member: {member_alias}")
        
        # Get reference member
        if current_entry.expected_rank is None:
            raise ValueError(f"No expected rank found for member: {member_alias}")
        
        ref_member = self.ranking_engine.get_reference_member(
            member_alias, member.role, current_entry.rank, current_entry.expected_rank
        )
        
        if not ref_member:
            raise ValueError("No suitable reference member found")
        
        # Calculate target weighted score
        ref_weighted_scores = self.ranking_engine.calculate_weighted_scores([ref_member], [member.role])
        ref_score = ref_weighted_scores[ref_member]
        
        # Determine direction (move up or down in rank)
        move_up = current_entry.expected_rank < current_entry.rank
        target_multiplier = 1 + (target_percent / 100) if move_up else 1 - (target_percent / 100)
        target_weighted_score = ref_score * target_multiplier
        
        # Get current weighted score
        current_weighted_scores = self.ranking_engine.calculate_weighted_scores([member_alias], [member.role])
        current_weighted_score = current_weighted_scores[member_alias]
        
        # Calculate needed delta
        needed_delta = target_weighted_score - current_weighted_score
        
        # Get applicable metrics and their weights
        applicable_metrics = self.ranking_engine.get_applicable_metrics(member.role)
        selected_applicable = [m for m in applicable_metrics if m.name in selected_metrics]
        
        if not selected_applicable:
            raise ValueError("No applicable metrics selected for adjustment")
        
        # Check if total weight is zero
        total_weight = sum(m.weights_by_role.get(member.role, 0.0) for m in selected_applicable)
        if total_weight == 0:
            raise ValueError("Selected metrics have zero total weight for this role")
        
        # Calculate proposed adjustments
        proposed_scores, achieved_score, hit_clamps = self._calculate_adjustments(
            member_alias, selected_applicable, needed_delta, member.role
        )
        
        return ScoreAdjustmentPreview(
            proposed=proposed_scores,
            achieved_weighted_score=achieved_score,
            hit_clamps=hit_clamps
        )
    
    def _calculate_adjustments(self, member_alias: str, metrics: List[Metric], 
                             needed_delta: float, role: str) -> Tuple[Dict[str, float], float, List[str]]:
        """Calculate score adjustments with iterative refinement."""
        
        # Get current scores
        member_scores = self.data_manager.get_member_scores()
        current_scores = member_scores.get(member_alias, {})
        
        # Initialize tracking variables
        proposed_scores = {}
        hit_clamps = []
        remaining_delta = needed_delta
        
        # Calculate initial proportional distribution
        total_weight = sum(m.weights_by_role.get(role, 0.0) for m in metrics)
        
        for iteration in range(settings.MAX_ADJUSTMENT_ITERATIONS):
            if abs(remaining_delta) < 0.001:  # Close enough
                break
            
            # Calculate available metrics (not yet clamped)
            available_metrics = [m for m in metrics if m.name not in hit_clamps]
            if not available_metrics:
                break
            
            available_weight = sum(m.weights_by_role.get(role, 0.0) for m in available_metrics)
            if available_weight == 0:
                break
            
            # Distribute remaining delta proportionally
            for metric in available_metrics:
                weight = metric.weights_by_role.get(role, 0.0)
                if weight == 0:
                    continue
                
                # Calculate proportional delta for this metric
                metric_delta = remaining_delta * (weight / available_weight)
                
                # Convert to raw score adjustment
                raw_score_delta = metric_delta / weight
                
                # Get current raw score
                current_raw_score = current_scores.get(metric.name, 0.0)
                if metric.name in proposed_scores:
                    current_raw_score = proposed_scores[metric.name]
                
                # Calculate new raw score
                new_raw_score = current_raw_score + raw_score_delta
                
                # Apply clamping
                clamped_score = max(metric.min_value, min(metric.max_value, new_raw_score))
                
                # Check if we hit a clamp
                if abs(clamped_score - new_raw_score) > 0.001:
                    if metric.name not in hit_clamps:
                        hit_clamps.append(metric.name)
                
                proposed_scores[metric.name] = clamped_score
            
            # Recalculate achieved delta
            achieved_delta = 0.0
            for metric in metrics:
                weight = metric.weights_by_role.get(role, 0.0)
                if weight == 0:
                    continue
                
                old_score = current_scores.get(metric.name, 0.0)
                new_score = proposed_scores.get(metric.name, old_score)
                score_change = new_score - old_score
                achieved_delta += score_change * weight
            
            remaining_delta = needed_delta - achieved_delta
            
            logger.debug(f"Iteration {iteration + 1}: achieved_delta={achieved_delta:.4f}, "
                        f"remaining_delta={remaining_delta:.4f}, hit_clamps={hit_clamps}")
        
        # Calculate final achieved weighted score
        current_weighted_score = self.ranking_engine.calculate_weighted_scores([member_alias], [role])[member_alias]
        achieved_weighted_score = current_weighted_score + (needed_delta - remaining_delta)
        
        return proposed_scores, achieved_weighted_score, hit_clamps
    
    def get_adjustment_diff_table(self, member_alias: str, proposed_scores: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Generate a diff table showing old, new, and delta values."""
        member_scores = self.data_manager.get_member_scores()
        current_scores = member_scores.get(member_alias, {})
        
        diff_table = {}
        
        for metric_name, new_score in proposed_scores.items():
            old_score = current_scores.get(metric_name, 0.0)
            delta = new_score - old_score
            
            diff_table[metric_name] = {
                'old': round(old_score, 4),
                'new': round(new_score, 4),
                'delta': round(delta, 4)
            }
        
        return diff_table
    
    def validate_target_achievable(self, member_alias: str, selected_metrics: List[str], 
                                 target_percent: float) -> Tuple[bool, str]:
        """Validate if the target adjustment is theoretically achievable."""
        try:
            preview = self.preview_adjustment(member_alias, selected_metrics, target_percent)
            
            # Check if we achieved close to the target
            # This is a simplified check - in practice you'd compare against the actual target
            if len(preview.hit_clamps) > 0:
                return False, f"Target not fully achievable due to clamping on metrics: {', '.join(preview.hit_clamps)}"
            
            return True, "Target is achievable"
            
        except Exception as e:
            return False, str(e)
