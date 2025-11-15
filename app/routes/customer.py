from flask import Blueprint, render_template, session, redirect, url_for
from .. import socketio

bp = Blueprint('customer', __name__, url_prefix='/customer')

@bp.route('/')
def customer_page():
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('auth.role_page'))
    return render_template('customer.html')