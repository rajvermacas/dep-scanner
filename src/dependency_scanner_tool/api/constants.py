"""Constants for API configuration."""

# Scanner Worker Status Update Intervals (in seconds)
WORKER_STATUS_UPDATE_INTERVAL = 30  # General status update interval
WORKER_PROGRESS_UPDATE_INTERVAL = 2  # Progress-specific update interval (files, download)

# Git Service Download Progress Logging
DOWNLOAD_PROGRESS_LOG_INTERVAL_BYTES = 5 * 1024 * 1024  # 5MB - Log download progress every 5MB
DOWNLOAD_CHUNK_SIZE = 2 * 1024 * 1024 # 2MB - Size of each download chunk

# Job Monitor Settings
JOB_MONITOR_STALE_THRESHOLD = 120  # seconds - Status considered stale after 2 minutes
JOB_MONITOR_CLEANUP_AGE_HOURS = 24  # hours - Clean up jobs older than 24 hours
