#!/usr/bin/env python3
"""
Script to update weights in the SQLite database to be between 0-1000.
"""

import sqlite3

def update_weights():
    """Update weights in the database to be between 0-1000."""
    try:
        conn = sqlite3.connect('ranking.db')
        cursor = conn.cursor()
        
        # First, check current weights
        cursor.execute('SELECT MIN(weight), MAX(weight), COUNT(*) FROM metric_weights')
        min_weight, max_weight, count = cursor.fetchone()
        print(f"Current weights: {count} entries, range {min_weight} to {max_weight}")
        
        # Check if weights are already in 0-1000 range
        if min_weight >= 0 and max_weight <= 1000:
            print("Weights are already in the 0-1000 range!")
            
            # Show some sample weights
            cursor.execute('''
                SELECT m.name, mw.role, mw.weight 
                FROM metrics m 
                JOIN metric_weights mw ON m.id = mw.metric_id 
                WHERE mw.weight > 0
                ORDER BY m.name, mw.role
                LIMIT 10
            ''')
            
            results = cursor.fetchall()
            print(f"\nSample weights (first 10 non-zero):")
            print(f"{'Metric':<25} {'Role':<10} {'Weight'}")
            print("-" * 50)
            
            for row in results:
                print(f"{row[0]:<25} {row[1]:<10} {row[2]}")
                
        else:
            print("Weights need to be updated to 0-1000 range")
            # If weights are in 0.0-1.0 range, multiply by 1000
            if max_weight <= 1.0:
                print("Converting from 0.0-1.0 range to 0-1000 range...")
                cursor.execute('UPDATE metric_weights SET weight = CAST(weight * 1000 AS INTEGER)')
                conn.commit()
                print("Weights updated successfully!")
            else:
                print("Weights are in an unexpected range. Manual review needed.")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_weights()
