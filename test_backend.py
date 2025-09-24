#!/usr/bin/env python3
"""Simple test script to verify backend functionality."""

import sys
import traceback
from backend.data_manager import DataManager
from backend.ranking_engine import RankingEngine
from backend.adjustment_engine import AdjustmentEngine

def test_data_loading():
    """Test data loading functionality."""
    print("Testing data loading...")
    
    try:
        # Test with CSV files since Excel might not be readable
        dm = DataManager("rank.xlsx")  # Will fallback to CSV
        dm.load_data()
        
        print("✓ Data loaded successfully")
        
        # Test basic data access
        members = dm.get_members()
        print(f"✓ Found {len(members)} members")
        
        roles = dm.get_roles()
        print(f"✓ Found {len(roles)} roles: {roles}")
        
        metrics = dm.get_metrics()
        print(f"✓ Found {len(metrics)} metrics")
        
        return dm
        
    except Exception as e:
        print(f"✗ Data loading failed: {e}")
        traceback.print_exc()
        return None

def test_ranking_engine(data_manager):
    """Test ranking engine functionality."""
    print("\nTesting ranking engine...")
    
    try:
        re = RankingEngine(data_manager)
        
        # Test weighted score calculation
        weighted_scores = re.calculate_weighted_scores()
        print(f"✓ Calculated weighted scores for {len(weighted_scores)} members")
        
        # Test ranking calculation
        rankings = re.calculate_rankings()
        print(f"✓ Calculated rankings for {len(rankings)} members")
        
        # Show some sample rankings
        for i, ranking in enumerate(rankings[:5]):
            print(f"  {ranking.alias} ({ranking.role}): Rank {ranking.rank}, Score {ranking.weighted_score:.4f}")
        
        # Test mismatches
        mismatches = re.get_mismatches()
        print(f"✓ Found {len(mismatches)} mismatches")
        
        return re
        
    except Exception as e:
        print(f"✗ Ranking engine failed: {e}")
        traceback.print_exc()
        return None

def test_adjustment_engine(data_manager, ranking_engine):
    """Test adjustment engine functionality."""
    print("\nTesting adjustment engine...")
    
    try:
        ae = AdjustmentEngine(data_manager, ranking_engine)
        
        # Find a member with a mismatch to test adjustment
        mismatches = ranking_engine.get_mismatches()
        if not mismatches:
            print("! No mismatches found, skipping adjustment test")
            return ae
        
        test_member = mismatches[0]
        print(f"Testing adjustment for {test_member.alias}")
        
        # Get applicable metrics
        applicable_metrics = ranking_engine.get_applicable_metrics(test_member.role)
        if not applicable_metrics:
            print("! No applicable metrics found, skipping adjustment test")
            return ae
        
        # Test preview
        selected_metrics = [applicable_metrics[0].name]  # Just test with first metric
        preview = ae.preview_adjustment(test_member.alias, selected_metrics, 5.0)
        
        print(f"✓ Preview generated: achieved score {preview.achieved_weighted_score:.4f}")
        print(f"  Proposed changes: {preview.proposed}")
        if preview.hit_clamps:
            print(f"  Hit clamps: {preview.hit_clamps}")
        
        return ae
        
    except Exception as e:
        print(f"✗ Adjustment engine failed: {e}")
        traceback.print_exc()
        return None

def main():
    """Run all tests."""
    print("=== Backend Test Suite ===\n")
    
    # Test data loading
    data_manager = test_data_loading()
    if not data_manager:
        print("\n✗ Cannot continue without data manager")
        sys.exit(1)
    
    # Test ranking engine
    ranking_engine = test_ranking_engine(data_manager)
    if not ranking_engine:
        print("\n✗ Cannot continue without ranking engine")
        sys.exit(1)
    
    # Test adjustment engine
    adjustment_engine = test_adjustment_engine(data_manager, ranking_engine)
    if not adjustment_engine:
        print("\n✗ Adjustment engine test failed")
        sys.exit(1)
    
    print("\n=== All Tests Passed! ===")
    print("Backend is ready to run.")

if __name__ == "__main__":
    main()
