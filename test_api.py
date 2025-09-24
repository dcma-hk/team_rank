#!/usr/bin/env python3
"""
Test script to verify the API is returning weights correctly.
"""

import requests
import json

def test_metrics_api():
    """Test the metrics API endpoint."""
    try:
        response = requests.get('http://localhost:8000/api/metrics')
        if response.status_code == 200:
            metrics = response.json()
            print(f"Found {len(metrics)} metrics")
            
            # Show first few metrics with their weights
            for i, metric in enumerate(metrics[:3]):
                print(f"\nMetric {i+1}: {metric['name']}")
                print("Weights by role:")
                for role, weight in metric['weights_by_role'].items():
                    if weight > 0:
                        print(f"  {role}: {weight}")
        else:
            print(f"API request failed: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_metrics_api()
