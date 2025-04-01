import cloudinary
from flask import Blueprint, request, jsonify
from models import db, User

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.route("/<username>", methods=["GET"])
def get_user(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    print(user)
    user_data = {
        "username": user.username,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "email": user.email,
        "bio": user.bio or "",
        "image": user.image or ""
    }
    return jsonify({"user": user_data}), 200


@profile_bp.route('/<username>', methods=['PUT'])
def update_user(username):
    data = request.json
    updated_user = User.update_user_settings(username, data)
    if not updated_user:
        return jsonify({"error": "User not found"}), 404
    
    user_data = {
        "username": updated_user.username,
        "firstname": updated_user.firstname,
        "lastname": updated_user.lastname,
        "email": updated_user.email,
        "bio": updated_user.bio or "",
        "image": updated_user.image or ""
    }
    db.session.commit()
    return jsonify({"user": user_data}), 200

@profile_bp.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        upload_result = cloudinary.uploader.upload(file)
        image_url = upload_result.get('secure_url')
        return jsonify({"imageUrl": image_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
