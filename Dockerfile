# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable for the database URL
ENV DATABASE_URL=""

# Run app.py when the container launches using a production-ready server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "app:app"]
