import os
from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    # Development mode
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
else:
    # Production mode - gunicorn will use this app object
    pass
