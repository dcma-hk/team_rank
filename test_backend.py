#!/usr/bin/env python3
"""Simple test script to verify backend functionality."""

import sys
import traceback
from backend.data_manager import DataManager
from backend.sqlite_data_manager import SQLiteDataManager
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

def test_sqlite_snapshots():
    """Test SQLite snapshot functionality."""
    print("\nTesting SQLite snapshot functionality...")

    try:
        # Create SQLite data manager
        sqlite_dm = SQLiteDataManager("test_snapshots.db")

        # Seed with mock data
        sqlite_dm.seed_mock_data()
        print("✓ Mock data seeded")

        # Test current snapshot
        current_snapshot = sqlite_dm.get_current_snapshot()
        print(f"✓ Current snapshot: {current_snapshot}")

        # Test getting available snapshots
        available_snapshots = sqlite_dm.get_available_snapshots()
        print(f"✓ Available snapshots: {available_snapshots}")

        # Test getting scores for current snapshot
        current_scores = sqlite_dm.get_member_scores()
        print(f"✓ Retrieved scores for current snapshot: {len(current_scores)} members")

        # Test getting scores for specific snapshot
        if available_snapshots:
            snapshot_scores = sqlite_dm.get_member_scores(snapshot=available_snapshots[0])
            print(f"✓ Retrieved scores for snapshot {available_snapshots[0]}: {len(snapshot_scores)} members")

        # Test updating scores with snapshot
        if current_scores:
            first_member = list(current_scores.keys())[0]
            first_metric = list(current_scores[first_member].keys())[0]
            original_score = current_scores[first_member][first_metric]

            # Update score
            new_score = original_score + 1.0 if original_score < 9.0 else original_score - 1.0
            sqlite_dm.update_member_scores(first_member, {first_metric: new_score})

            # Verify update
            updated_scores = sqlite_dm.get_member_scores()
            updated_score = updated_scores[first_member][first_metric]
            print(f"✓ Updated score for {first_member}.{first_metric}: {original_score} -> {updated_score}")

        # Test ranking engine with snapshots
        re = RankingEngine(sqlite_dm)
        rankings = re.calculate_rankings()
        print(f"✓ Calculated rankings with snapshot support: {len(rankings)} members")

        # Clean up test database
        import os
        if os.path.exists("test_snapshots.db"):
            os.remove("test_snapshots.db")
        print("✓ Test database cleaned up")

        return True

    except Exception as e:
        print(f"✗ SQLite snapshot test failed: {e}")
        traceback.print_exc()
        return False

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

    # Test SQLite snapshots
    snapshot_test_passed = test_sqlite_snapshots()
    if not snapshot_test_passed:
        print("\n✗ SQLite snapshot test failed")
        sys.exit(1)

    print("\n=== All Tests Passed! ===")
    print("Backend is ready to run with snapshot support.")

if __name__ == "__main__":
    main()
