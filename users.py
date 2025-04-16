from flask import Blueprint, request, jsonify
from models import db, User
from datetime import datetime
users_bp = Blueprint('users', __name__, url_prefix='/api/users')

@users_bp.route('', methods=['GET'])
def get_users():
    users = User.query.all()
    users_list = []
    for user in users:
        user_data = {
            'id': user.id,
            'firstname': user.firstname,
            'lastname': user.lastname,
            'username': user.username,
            'email': user.email,
            'bio': user.bio,
            'role': user.role,
        }
        users_list.append(user_data)
    return jsonify(users_list), 200