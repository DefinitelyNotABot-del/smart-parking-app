from flask import Blueprint, render_template, session, redirect, url_for
from .. import socketio

bp = Blueprint('owner', __name__, url_prefix='/owner')

@bp.route('/')
def owner_page():
    if 'user_id' not in session or session.get('role') != 'owner':
        return redirect(url_for('auth.role_page'))
    return render_template('owner.html')

@bp.route('/lot/<int:lot_id>')
def lot_spots_page(lot_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        return redirect(url_for('auth.role_page'))
    return render_template('lot_spots.html')