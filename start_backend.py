#!/usr/bin/env python3
"""Start the backend server."""

import uvicorn

if __name__ == "__main__":
    print("Starting Team Stack Ranking Manager backend...")
    print("Backend will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
