#!/usr/bin/env python3
"""Start the backend server with SQLite data source."""

import os
import sys
from pathlib import Path

# Set environment variables for SQLite
os.environ['DATA_SOURCE'] = 'sqlite'
os.environ['SQLITE_PATH'] = 'ranking.db'
os.environ['PORT'] = '8000'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000'

# Import and run the main application
if __name__ == "__main__":
    # Check if we should seed mock data
    if len(sys.argv) > 1 and sys.argv[1] == "--seed":
        print("Seeding mock data...")
        try:
            from backend.data_manager_factory import create_data_manager
            manager = create_data_manager()
            if hasattr(manager, 'seed_mock_data'):
                manager.seed_mock_data()
                print("Mock data seeded successfully!")
            else:
                print("Mock data seeding not available for this data source")
        except Exception as e:
            print(f"Error seeding data: {e}")
            sys.exit(1)
    else:
        # Start the server
        import uvicorn
        from main import app
        
        print("Starting server with SQLite data source...")
        print(f"Database: {os.environ['SQLITE_PATH']}")
        print(f"Port: {os.environ['PORT']}")
        
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ['PORT']))
