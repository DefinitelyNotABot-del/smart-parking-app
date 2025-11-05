import os
import requests

# Set the FLASK_ENV environment variable to development
os.environ['FLASK_ENV'] = 'development'

# Define the URL for the reset-database endpoint
reset_url = "http://127.0.0.1:5000/api/reset-database"

print(f"Attempting to reset database at {reset_url}...")

try:
    # Send a POST request to the reset-database endpoint
    response = requests.post(reset_url)
    response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

    print("Database reset successful!")
    print(f"Response: {response.json()}")
except requests.exceptions.ConnectionError:
    print("Error: Could not connect to the Flask application.")
    print("Please ensure your Flask application is running before running this script.")
except requests.exceptions.RequestException as e:
    print(f"An error occurred during the request: {e}")
    if response is not None:
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

# Keep the console window open for a moment to see the output
input("Press Enter to exit...")
