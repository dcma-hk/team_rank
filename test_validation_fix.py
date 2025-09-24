#!/usr/bin/env python3
"""
Test script to verify the validation logic fix.
"""

import sys
import os
sys.path.append('.')

from backend.data_manager_factory import DataManagerFactory
from backend.ranking_engine import RankingEngine
from backend.adjustment_engine import AdjustmentEngine

def test_validation_fix():
    """Test the fixed validation logic."""
    print("Testing validation logic fix...")
    
    try:
        # Initialize components
        data_manager = DataManagerFactory.create_data_manager("ranking.db")
        ranking_engine = RankingEngine(data_manager)
        adjustment_engine = AdjustmentEngine(data_manager, ranking_engine)
        
        # Get all rankings to find a member with expected rank
        rankings = ranking_engine.calculate_rankings()
        
        # Find a member with expected rank set
        test_member = None
        for ranking in rankings:
            if ranking.expected_rank is not None and ranking.expected_rank != ranking.rank:
                test_member = ranking
                break
        
        if not test_member:
            print("No member found with expected rank different from current rank")
            return
        
        print(f"Testing with member: {test_member.alias}")
        print(f"  Current rank: {test_member.rank}")
        print(f"  Expected rank: {test_member.expected_rank}")
        
        # Test case 1: Small change that should be valid
        small_changes = {"metric1": 0.1}
        is_valid, message = adjustment_engine.validate_one_level_restriction(test_member.alias, small_changes)
        print(f"  Small change validation: {'✓' if is_valid else '✗'} - {message}")
        
        # Test case 2: Large change that should violate the restriction
        # Get applicable metrics for this member
        members = data_manager.get_members()
        member = next((m for m in members if m.alias == test_member.alias), None)
        if member:
            metrics = data_manager.get_metrics()
            applicable_metrics = [m for m in metrics if (m.weights_by_role.get(member.role, 0) > 0)]
            
            if applicable_metrics:
                # Make a large change to the first applicable metric
                metric_name = applicable_metrics[0].name
                large_changes = {metric_name: 10.0}  # Maximum score
                
                is_valid, message = adjustment_engine.validate_one_level_restriction(test_member.alias, large_changes)
                print(f"  Large change validation: {'✓' if is_valid else '✗'} - {message}")
                
                # Check if the error message format is correct
                if not is_valid and "ranks away from expected rank" in message:
                    print("✓ Validation logic fix is working correctly!")
                elif not is_valid:
                    print(f"⚠ Validation logic may need adjustment. Message: {message}")
                else:
                    print("⚠ Large change was unexpectedly valid")
            else:
                print("No applicable metrics found for this member")
        else:
            print("Member not found in members list")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_validation_fix()
