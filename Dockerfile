# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Create data directory for SQLite (if used)
RUN mkdir -p data

# Make port 8080 available (Cloud Run expects this port)
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run app.py with gunicorn using eventlet for SocketIO support
CMD exec gunicorn --bind :$PORT --workers 1 --worker-class eventlet --timeout 120 app:app
