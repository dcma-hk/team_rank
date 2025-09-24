#!/usr/bin/env python3
"""
Test script to verify the reference member fix.
"""

import sys
import os
sys.path.append('.')

from backend.data_manager_factory import DataManagerFactory
from backend.ranking_engine import RankingEngine

def test_reference_member_fix():
    """Test the fixed reference member logic."""
    print("Testing reference member fix...")
    
    try:
        # Initialize components
        data_manager = DataManagerFactory.create_data_manager("ranking.db")
        ranking_engine = RankingEngine(data_manager)
        
        # Get all rankings for Dev role (based on the screenshot)
        dev_rankings = ranking_engine.calculate_rankings(["Dev"])
        
        print("Current Dev rankings:")
        for ranking in sorted(dev_rankings, key=lambda x: x.rank):
            expected_str = f" (expected: {ranking.expected_rank})" if ranking.expected_rank else ""
            print(f"  {ranking.alias}: Rank {ranking.rank}{expected_str}")
        
        # Test case: Dev02 with expected rank 2, but no member at rank 2
        # Should find Dev09 at rank 3 as reference
        test_member = "Dev02"
        test_member_ranking = next((r for r in dev_rankings if r.alias == test_member), None)
        
        if not test_member_ranking:
            print(f"Member {test_member} not found")
            return
        
        if not test_member_ranking.expected_rank:
            print(f"Member {test_member} has no expected rank set")
            return
        
        print(f"\nTesting reference member for {test_member}:")
        print(f"  Current rank: {test_member_ranking.rank}")
        print(f"  Expected rank: {test_member_ranking.expected_rank}")
        
        # Test the get_reference_member method
        ref_member_alias = ranking_engine.get_reference_member(
            test_member, 
            test_member_ranking.role, 
            test_member_ranking.rank, 
            test_member_ranking.expected_rank
        )
        
        if ref_member_alias:
            ref_member_ranking = next((r for r in dev_rankings if r.alias == ref_member_alias), None)
            if ref_member_ranking:
                print(f"  Reference member found: {ref_member_alias} at rank {ref_member_ranking.rank}")
                
                # Check if this is the expected behavior
                if test_member_ranking.expected_rank == 2:
                    # Should find the next available member at rank >= 2
                    expected_ref_rank = min(r.rank for r in dev_rankings if r.rank >= 2 and r.alias != test_member)
                    if ref_member_ranking.rank == expected_ref_rank:
                        print("✓ Reference member selection is working correctly!")
                    else:
                        print(f"⚠ Expected reference at rank {expected_ref_rank}, but got rank {ref_member_ranking.rank}")
                else:
                    print(f"  Reference member at rank {ref_member_ranking.rank}")
            else:
                print(f"  Reference member {ref_member_alias} not found in rankings")
        else:
            print("  No reference member found")
        
        # Test another case where exact rank exists
        print(f"\nTesting with a member that has an exact rank match...")
        for ranking in dev_rankings:
            if ranking.expected_rank and ranking.expected_rank != ranking.rank:
                # Check if there's a member at the expected rank
                exact_match = any(r.rank == ranking.expected_rank and r.alias != ranking.alias for r in dev_rankings)
                if exact_match:
                    ref_alias = ranking_engine.get_reference_member(
                        ranking.alias, 
                        ranking.role, 
                        ranking.rank, 
                        ranking.expected_rank
                    )
                    if ref_alias:
                        ref_ranking = next((r for r in dev_rankings if r.alias == ref_alias), None)
                        print(f"  {ranking.alias} (rank {ranking.rank}, expected {ranking.expected_rank}) -> {ref_alias} (rank {ref_ranking.rank if ref_ranking else 'unknown'})")
                    break
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reference_member_fix()
