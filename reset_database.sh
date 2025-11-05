#!/bin/bash

# This script sends a POST request to the /api/reset-database endpoint
# to reset the application's database. It will only work if the
# FLASK_ENV environment variable is set to 'development'.

curl -X POST http://127.0.0.1:5000/api/reset-database
