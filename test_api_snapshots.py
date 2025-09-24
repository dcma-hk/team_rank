#!/usr/bin/env python3
"""Test the snapshot API endpoints."""

import requests
import json
import sys

def test_snapshots_endpoint():
    """Test the /api/snapshots endpoint."""
    try:
        response = requests.get("http://localhost:8000/api/snapshots")
        if response.status_code == 200:
            data = response.json()
            print("✓ Snapshots endpoint working")
            print(f"  Current snapshot: {data.get('current_snapshot')}")
            print(f"  Available snapshots: {data.get('available_snapshots')}")
            return True
        else:
            print(f"✗ Snapshots endpoint failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error testing snapshots endpoint: {e}")
        return False

def test_scores_with_snapshot():
    """Test the /api/scores endpoint with snapshot parameter."""
    try:
        # Test without snapshot parameter
        response = requests.get("http://localhost:8000/api/scores")
        if response.status_code == 200:
            data = response.json()
            print("✓ Scores endpoint working")
            print(f"  Current snapshot: {data.get('current_snapshot')}")
            print(f"  Available snapshots: {data.get('available_snapshots')}")
            print(f"  Number of members: {len(data.get('scores', {}))}")
            
            # Test with specific snapshot if available
            available_snapshots = data.get('available_snapshots', [])
            if available_snapshots:
                snapshot = available_snapshots[0]
                response2 = requests.get(f"http://localhost:8000/api/scores?snapshot={snapshot}")
                if response2.status_code == 200:
                    data2 = response2.json()
                    print(f"✓ Scores endpoint with snapshot {snapshot} working")
                    print(f"  Number of members: {len(data2.get('scores', {}))}")
                else:
                    print(f"✗ Scores endpoint with snapshot failed: {response2.status_code}")
                    return False
            
            return True
        else:
            print(f"✗ Scores endpoint failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error testing scores endpoint: {e}")
        return False

def test_rankings_with_snapshot():
    """Test the /api/rankings endpoint with snapshot parameter."""
    try:
        # Test without snapshot parameter
        response = requests.get("http://localhost:8000/api/rankings")
        if response.status_code == 200:
            data = response.json()
            print("✓ Rankings endpoint working")
            print(f"  Number of rankings: {len(data)}")
            
            # Test with specific snapshot if we can get available snapshots
            snapshots_response = requests.get("http://localhost:8000/api/snapshots")
            if snapshots_response.status_code == 200:
                snapshots_data = snapshots_response.json()
                available_snapshots = snapshots_data.get('available_snapshots', [])
                if available_snapshots:
                    snapshot = available_snapshots[0]
                    response2 = requests.get(f"http://localhost:8000/api/rankings?snapshot={snapshot}")
                    if response2.status_code == 200:
                        data2 = response2.json()
                        print(f"✓ Rankings endpoint with snapshot {snapshot} working")
                        print(f"  Number of rankings: {len(data2)}")
                    else:
                        print(f"✗ Rankings endpoint with snapshot failed: {response2.status_code}")
                        return False
            
            return True
        else:
            print(f"✗ Rankings endpoint failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error testing rankings endpoint: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing Snapshot API Endpoints ===\n")
    
    success = True
    
    if not test_snapshots_endpoint():
        success = False
    
    print()
    if not test_scores_with_snapshot():
        success = False
    
    print()
    if not test_rankings_with_snapshot():
        success = False
    
    if success:
        print("\n✓ All snapshot API tests passed!")
    else:
        print("\n✗ Some API tests failed!")
        sys.exit(1)
