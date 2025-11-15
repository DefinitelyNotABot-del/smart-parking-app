import sqlite3
import click
from flask import current_app, g, session

def get_db_path():
    """Get the appropriate database path based on current user session."""
    # Determine which database to use based on session
    # This logic is now centralized here.
    if session.get('is_demo'):
        # In the new structure, we get the path from the app config
        return current_app.config['DEMO_DATABASE']
    return current_app.config['DATABASE']

def get_db():
    """
    Opens a new database connection if there is none yet for the
    current application context.
    """
    if 'db' not in g:
        db_path = get_db_path()
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db_path = db_path  # Track which DB we're using
    return g.db

def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)

    if db is not None:
        db.close()

def get_cursor():
    """Gets a cursor from the request-bound database connection."""
    return get_db().cursor()

@click.command('init-db')
def init_db_command():
    """CLI command to clear the existing data and create new tables."""
    # The actual schema creation logic is in db_setup.py
    from .services.db_setup import init_db_for_path
    
    # This command will initialize the REGULAR database by default
    # as it runs outside a request context.
    init_db_for_path(current_app.config['DATABASE'], force_reset=True)
    click.echo(f"Initialized the regular database at {current_app.config['DATABASE']}.")


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
