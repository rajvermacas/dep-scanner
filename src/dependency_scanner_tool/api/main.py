"""Main entry point for the REST API server."""

import logging
import uvicorn
from dependency_scanner_tool.api.app import app


def setup_logging():
    """Configure logging for the FastAPI application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console output
        ]
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger("dependency_scanner_tool").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


if __name__ == "__main__":
    setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)