"""Core ranking algorithm implementation."""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd

from backend.models import Member, Metric, RankingEntry
from backend.data_manager import DataManager

logger = logging.getLogger(__name__)


class RankingEngine:
    """Handles weighted score calculation and ranking logic."""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
    
    def calculate_weighted_scores(self, members: Optional[List[str]] = None,
                                roles: Optional[List[str]] = None,
                                snapshot: Optional[str] = None) -> Dict[str, float]:
        """Calculate weighted scores for specified members and roles, optionally filtered by snapshot."""
        if members is None:
            members = [m.alias for m in self.data_manager.get_members()]

        if roles is None:
            roles = self.data_manager.get_roles()

        # Get member-role mapping
        member_roles = {}
        for member in self.data_manager.get_members():
            if member.alias in members and member.role in roles:
                member_roles[member.alias] = member.role

        # Get metrics and scores
        metrics = self.data_manager.get_metrics()

        # Check if data manager supports snapshot parameter
        if hasattr(self.data_manager, 'get_member_scores') and 'snapshot' in self.data_manager.get_member_scores.__code__.co_varnames:
            member_scores = self.data_manager.get_member_scores(snapshot=snapshot)
        else:
            member_scores = self.data_manager.get_member_scores()
        
        weighted_scores = {}
        
        for member_alias, role in member_roles.items():
            if member_alias not in member_scores:
                logger.warning(f"No scores found for member: {member_alias}")
                weighted_scores[member_alias] = 0.0
                continue
            
            total_weighted_score = 0.0
            
            for metric in metrics:
                # Only consider metrics with weight > 0 for this role
                weight = metric.weights_by_role.get(role, 0.0)
                if weight <= 0:
                    continue
                
                # Get member's raw score for this metric
                raw_score = member_scores[member_alias].get(metric.name, 0.0)
                
                # Calculate contribution: score × weight
                contribution = raw_score * weight
                total_weighted_score += contribution
            
            weighted_scores[member_alias] = total_weighted_score
        
        return weighted_scores
    
    def calculate_rankings(self, roles: Optional[List[str]] = None, snapshot: Optional[str] = None) -> List[RankingEntry]:
        """Calculate rankings within role cohorts using dense ranking, optionally filtered by snapshot."""
        if roles is None:
            roles = self.data_manager.get_roles()

        # Get all members for specified roles
        all_members = self.data_manager.get_members()
        filtered_members = [m for m in all_members if m.role in roles]

        # Calculate weighted scores
        member_aliases = [m.alias for m in filtered_members]
        weighted_scores = self.calculate_weighted_scores(member_aliases, roles, snapshot=snapshot)
        
        # Get expected rankings
        expected_rankings = self.data_manager.get_expected_rankings()
        
        # Group members by role and rank within each role
        rankings = []
        
        for role in roles:
            role_members = [m for m in filtered_members if m.role == role]
            if not role_members:
                continue
            
            # Create list of (member, weighted_score) tuples
            role_data = []
            for member in role_members:
                score = weighted_scores.get(member.alias, 0.0)
                role_data.append((member, score))
            
            # Sort by weighted score (descending), then by alias for tie-breaking
            role_data.sort(key=lambda x: (-x[1], x[0].alias))
            
            # Apply dense ranking
            current_rank = 1
            prev_score = None
            
            for i, (member, score) in enumerate(role_data):
                # Dense ranking: same score = same rank, next different score gets next rank
                if prev_score is not None and score != prev_score:
                    current_rank = i + 1
                
                expected_rank = expected_rankings.get(member.alias)
                mismatch = expected_rank is not None and expected_rank != current_rank
                
                ranking_entry = RankingEntry(
                    alias=member.alias,
                    role=member.role,
                    weighted_score=round(score, 4),
                    rank=current_rank,
                    expected_rank=expected_rank,
                    mismatch=mismatch
                )
                
                rankings.append(ranking_entry)
                prev_score = score
        
        return rankings
    
    def get_mismatches(self) -> List[RankingEntry]:
        """Get all members with rank ≠ expected rank, ordered by priority."""
        all_rankings = self.calculate_rankings()
        mismatches = [r for r in all_rankings if r.mismatch]
        
        # Sort by role, then by the magnitude of rank difference
        def sort_key(entry):
            rank_diff = abs(entry.rank - (entry.expected_rank or entry.rank))
            return (entry.role, -rank_diff, entry.alias)
        
        mismatches.sort(key=sort_key)
        return mismatches
    
    def get_reference_member(self, target_member: str, target_role: str,
                           current_rank: int, expected_rank: int) -> Optional[str]:
        """Get reference member for score adjustment."""
        if expected_rank == current_rank:
            return None

        # Get all members in the same role, sorted by rank
        role_rankings = [r for r in self.calculate_rankings([target_role]) if r.role == target_role]
        role_rankings.sort(key=lambda x: x.rank)

        if expected_rank < current_rank:
            # Need to improve rank (move up), find member at expected rank or next available rank
            target_ref_rank = expected_rank if expected_rank > 1 else 1

            # First try to find exact match at expected rank
            for entry in role_rankings:
                if entry.rank == target_ref_rank and entry.alias != target_member:
                    return entry.alias

            # If no exact match, find the next available member at a rank >= expected_rank
            for entry in role_rankings:
                if entry.rank >= target_ref_rank and entry.alias != target_member:
                    return entry.alias
        else:
            # Need to worsen rank (move down), find member at expected rank or next available rank
            target_ref_rank = expected_rank

            # First try to find exact match at expected rank
            for entry in role_rankings:
                if entry.rank == target_ref_rank and entry.alias != target_member:
                    return entry.alias

            # If no exact match, find the next available member at a rank >= expected_rank
            for entry in role_rankings:
                if entry.rank >= target_ref_rank and entry.alias != target_member:
                    return entry.alias

        return None
    
    def get_applicable_metrics(self, role: str) -> List[Metric]:
        """Get metrics applicable to a specific role (weight > 0)."""
        all_metrics = self.data_manager.get_metrics()
        applicable = []
        
        for metric in all_metrics:
            weight = metric.weights_by_role.get(role, 0.0)
            if weight > 0:
                applicable.append(metric)
        
        return applicable
