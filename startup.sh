#!/bin/bash
# Startup script for Azure App Service

echo "Starting Smart Parking App deployment..."

# Create instance directory if it doesn't exist
mkdir -p instance

# Start the application with gunicorn
# Database auto-initialization happens when app starts
echo "Starting gunicorn server (databases will auto-initialize on first run)..."
exec gunicorn --bind 0.0.0.0:$PORT --worker-class eventlet --workers 1 --timeout 120 --log-level info --access-logfile - --error-logfile - run:app
