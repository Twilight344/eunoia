from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from db import client

bp = Blueprint('emotion', __name__)
db = client["mental_health_db"]
emotions = db["emotions"]
user_options = db["user_options"]  # Store custom options for each user

# POST /api/emotion - log a mood
@bp.route('/api/emotion', methods=['POST'])
@jwt_required()
def log_emotion():
    user_id = get_jwt_identity()
    data = request.get_json()
    mood = data.get('mood')
    note = data.get('note', '')
    intensity = data.get('intensity')
    location = data.get('location', '')
    company = data.get('company', '')
    activity = data.get('activity', '')
    
    if not mood:
        return jsonify({'error': 'Mood is required'}), 400
    
    emotions.insert_one({
        'user_id': ObjectId(user_id),
        'timestamp': datetime.now(),
        'mood': mood,
        'note': note,
        'intensity': int(intensity) if intensity is not None else None,
        'location': location,
        'company': company,
        'activity': activity
    })
    return jsonify({'message': 'Mood logged successfully'})

# GET /api/emotion - get all moods for user
@bp.route('/api/emotion', methods=['GET'])
@jwt_required()
def get_emotions():
    user_id = get_jwt_identity()
    logs = list(emotions.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1))
    for log in logs:
        log['id'] = str(log['_id'])
        log['timestamp'] = log['timestamp'].isoformat()
        del log['_id']
        del log['user_id']
    return jsonify(logs)

# GET /api/user-options - get user's custom options
@bp.route('/api/user-options', methods=['GET'])
@jwt_required()
def get_user_options():
    user_id = get_jwt_identity()
    user_doc = user_options.find_one({'user_id': ObjectId(user_id)})
    if user_doc:
        return jsonify({
            'locations': user_doc.get('locations', []),
            'companies': user_doc.get('companies', []),
            'activities': user_doc.get('activities', [])
        })
    return jsonify({
        'locations': [],
        'companies': [],
        'activities': []
    })

# POST /api/user-options - add custom options
@bp.route('/api/user-options', methods=['POST'])
@jwt_required()
def add_user_option():
    user_id = get_jwt_identity()
    data = request.get_json()
    option_type = data.get('type')  # 'location', 'company', or 'activity'
    option_value = data.get('value')
    
    if not option_type or not option_value:
        return jsonify({'error': 'Type and value are required'}), 400
    
    # Correct pluralization
    plural_map = {
        'location': 'locations',
        'company': 'companies',
        'activity': 'activities'
    }
    field = plural_map.get(option_type)
    if not field:
        return jsonify({'error': 'Invalid type'}), 400

    # Upsert user options
    user_options.update_one(
        {'user_id': ObjectId(user_id)},
        {
            '$addToSet': {field: option_value}
        },
        upsert=True
    )
    
    return jsonify({'message': f'{option_type} option added successfully'})

# (Optional) DELETE /api/emotion/<id> - delete a mood log
@bp.route('/api/emotion/<log_id>', methods=['DELETE'])
@jwt_required()
def delete_emotion(log_id):
    user_id = get_jwt_identity()
    emotions.delete_one({'_id': ObjectId(log_id), 'user_id': ObjectId(user_id)})
    return jsonify({'message': 'Deleted'})
