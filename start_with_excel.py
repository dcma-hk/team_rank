#!/usr/bin/env python3
"""Start the backend server with Excel/CSV data source."""

import os
import sys

# Set environment variables for Excel/CSV
os.environ['DATA_SOURCE'] = 'excel'
os.environ['EXCEL_PATH'] = 'rank.xlsx'
os.environ['PORT'] = '8000'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000'

# Import and run the main application
if __name__ == "__main__":
    import uvicorn
    from main import app
    
    print("Starting server with Excel/CSV data source...")
    print(f"Excel path: {os.environ['EXCEL_PATH']}")
    print(f"Port: {os.environ['PORT']}")
    
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ['PORT']))
