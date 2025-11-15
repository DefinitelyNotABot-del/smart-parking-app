#!/bin/bash
# Startup script for Azure App Service

echo "Starting Smart Parking App deployment..."

# Create instance directory if it doesn't exist
mkdir -p instance

# Set environment variables for better memory management
export PYTHONUNBUFFERED=1
export MALLOC_TRIM_THRESHOLD_=100000

# Start the application with gunicorn
# Database auto-initialization happens when app starts
echo "Starting gunicorn server (databases will auto-initialize on first run)..."
# Increased timeout to 300s, added max-requests to prevent memory leaks
exec gunicorn --bind 0.0.0.0:$PORT \
    --worker-class eventlet \
    --workers 1 \
    --timeout 300 \
    --graceful-timeout 60 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    run:app
