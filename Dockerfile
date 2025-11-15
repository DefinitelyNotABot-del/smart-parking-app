# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Make port 8000 available (Azure default)
EXPOSE 8000

# Define environment variable for the database URL
ENV DATABASE_URL=""
ENV PORT=8000

# Create instance directory (databases will auto-initialize on first app start)
RUN mkdir -p instance

# Run with gunicorn using eventlet workers for SocketIO support
# Database setup happens automatically when app starts
CMD gunicorn --bind 0.0.0.0:$PORT --worker-class eventlet --workers 1 --timeout 120 run:app
