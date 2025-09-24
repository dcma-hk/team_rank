#!/usr/bin/env python3
"""
Script to check current weights in the SQLite database.
"""

import sqlite3

def check_weights():
    """Check current weights in the database."""
    try:
        conn = sqlite3.connect('ranking.db')
        cursor = conn.cursor()
        
        # Get all weights
        cursor.execute('''
            SELECT m.name, mw.role, mw.weight 
            FROM metrics m 
            JOIN metric_weights mw ON m.id = mw.metric_id 
            ORDER BY m.name, mw.role
        ''')
        
        results = cursor.fetchall()
        print(f"Found {len(results)} weight entries:")
        print(f"{'Metric':<25} {'Role':<10} {'Weight'}")
        print("-" * 50)
        
        for row in results:
            print(f"{row[0]:<25} {row[1]:<10} {row[2]}")
        
        # Check weight ranges
        cursor.execute('SELECT MIN(weight), MAX(weight) FROM metric_weights')
        min_weight, max_weight = cursor.fetchone()
        print(f"\nWeight range: {min_weight} to {max_weight}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_weights()
