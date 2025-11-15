import os
import logging
import sqlite3
from datetime import datetime, timedelta

import click
import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from flask import (Flask, g, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_socketio import SocketIO
from werkzeug.security import check_password_hash, generate_password_hash



# Initialize extensions without an app
socketio = SocketIO()

def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True, template_folder='../templates')
    
    # --- Configuration ---
    # Load environment variables from .env file
    load_dotenv(os.path.join(app.root_path, '..', '.env'))

    app.config.from_mapping(
        SECRET_KEY=os.getenv('FLASK_SECRET_KEY', 'dev_fallback_secret_key_12345'),
        # Define database paths relative to the instance folder
        DATABASE=os.path.join(app.instance_path, 'parking.db'),
        DEMO_DATABASE=os.path.join(app.instance_path, 'demo.db'),
    )

    # Configure logging to stdout
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app.logger.setLevel(logging.DEBUG)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --- Initialize Extensions ---
    socketio.init_app(app)

    # --- Database Initialization ---
    from . import db
    db.init_app(app)
    
    # --- Auto-setup databases on first run ---
    from .setup import ensure_databases_ready
    with app.app_context():
        ensure_databases_ready(app)

    # --- Register Blueprints ---
    from .routes import auth, owner, customer, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(owner.bp)
    app.register_blueprint(customer.bp)
    app.register_blueprint(api.bp)

    return app
