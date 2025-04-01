from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import jwt
import datetime
from config import Config

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/signup', methods=['POST'])
def register():
    
    data = request.json
    required_fields = ['firstname', 'lastname', 'username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"{field} is required"}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({"message": "Username already exists"}), 400

    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        firstname=data['firstname'],
        lastname=data['lastname'],
        username=data['username'],
        email=data['email'],
        password=hashed_password,
        bio=data.get('bio', ''),
        image=data.get('image', ''),
        role=data.get('role', 'student')
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    if 'username' not in data or 'password' not in data:
        return jsonify({"message": "Username and password are required"}), 400

    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, Config.DB_SECRET_KEY, algorithm="HS256")
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "username": user.username,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "email": user.email,
                "role": user.role
            }
        }), 200
    return jsonify({"message": "Invalid credentials"}), 401
