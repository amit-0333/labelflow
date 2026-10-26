from flask import Blueprint, render_template, request, redirect
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from core.db import db
from core.models import User
from auth.decorators import role_required

auth_bp = Blueprint("auth", __name__)


## when someone hits '/register' show the register page
@auth_bp.route('/register')
def register():
    return render_template('register.html')


## take form data, save the user in database, then go to login page
@auth_bp.route('/perform_registration', methods=['POST'])
def perform_registration():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    ## stop duplicates
    if User.query.filter_by(username=username).first():
        return render_template('register.html', message="Username already taken")
    if User.query.filter_by(email=email).first():
        return render_template('register.html', message="Email already used")

    ## first user ever becomes admin, everyone else is annotator
    if User.query.count() == 0:
        role = "admin"
    else:
        role = "annotator"

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()

    return render_template('login.html', message="Registration successful, kindly login")


## when someone hits '/login' show the login page
@auth_bp.route('/login')
def login():
    return render_template('login.html')


## check username and password, if correct then login
@auth_bp.route('/perform_login', methods=['POST'])
def perform_login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return redirect('/')
    else:
        return render_template('login.html', message="Wrong username or password")


## logout and go back to login page
@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect('/login')


## admin only: show all users
@auth_bp.route('/admin/users')
@role_required("admin")
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)


## admin only: change role of one user
@auth_bp.route('/perform_role_change', methods=['POST'])
@role_required("admin")
def perform_role_change():
    user_id = request.form.get('user_id')
    new_role = request.form.get('role')

    user = User.query.get(int(user_id))
    user.role = new_role
    db.session.commit()

    users = User.query.all()
    return render_template('manage_users.html', users=users, message="Role updated")