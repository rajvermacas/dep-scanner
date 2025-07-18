"""Main entry point for the REST API server."""

import uvicorn
from dependency_scanner_tool.api.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)