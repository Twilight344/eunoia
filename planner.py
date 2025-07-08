from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime, timedelta
from db import client

bp = Blueprint('planner', __name__)
db = client["mental_health_db"]
todos = db["todos"]
timetables = db["timetables"]

# POST /api/todos - create a new todo
@bp.route('/api/todos', methods=['POST'])
@jwt_required()
def create_todo():
    user_id = get_jwt_identity()
    data = request.get_json()
    title = data.get('title')
    description = data.get('description', '')
    priority = data.get('priority', 'medium')  # low, medium, high
    due_date = data.get('due_date')
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    todo = {
        'user_id': ObjectId(user_id),
        'title': title,
        'description': description,
        'priority': priority,
        'completed': False,
        'created_at': datetime.now(),
        'due_date': datetime.fromisoformat(due_date) if due_date else None
    }
    
    result = todos.insert_one(todo)
    todo['id'] = str(result.inserted_id)
    todo['created_at'] = todo['created_at'].isoformat()
    if todo['due_date']:
        todo['due_date'] = todo['due_date'].isoformat()
    del todo['_id']
    del todo['user_id']
    
    return jsonify(todo), 201

# GET /api/todos - get all todos for user
@bp.route('/api/todos', methods=['GET'])
@jwt_required()
def get_todos():
    user_id = get_jwt_identity()
    user_todos = list(todos.find({'user_id': ObjectId(user_id)}).sort('created_at', -1))
    
    for todo in user_todos:
        todo['id'] = str(todo['_id'])
        todo['created_at'] = todo['created_at'].isoformat()
        if todo.get('due_date'):
            todo['due_date'] = todo['due_date'].isoformat()
        del todo['_id']
        del todo['user_id']
    
    return jsonify(user_todos)

# PUT /api/todos/<id> - update a todo
@bp.route('/api/todos/<todo_id>', methods=['PUT'])
@jwt_required()
def update_todo(todo_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    
    update_data = {}
    if 'title' in data:
        update_data['title'] = data['title']
    if 'description' in data:
        update_data['description'] = data['description']
    if 'priority' in data:
        update_data['priority'] = data['priority']
    if 'completed' in data:
        update_data['completed'] = data['completed']
    if 'due_date' in data:
        update_data['due_date'] = datetime.fromisoformat(data['due_date']) if data['due_date'] else None
    
    if not update_data:
        return jsonify({'error': 'No fields to update'}), 400
    
    result = todos.update_one(
        {'_id': ObjectId(todo_id), 'user_id': ObjectId(user_id)},
        {'$set': update_data}
    )
    
    if result.modified_count == 0:
        return jsonify({'error': 'Todo not found'}), 404
    
    return jsonify({'message': 'Todo updated successfully'})

# DELETE /api/todos/<id> - delete a todo
@bp.route('/api/todos/<todo_id>', methods=['DELETE'])
@jwt_required()
def delete_todo(todo_id):
    user_id = get_jwt_identity()
    result = todos.delete_one({'_id': ObjectId(todo_id), 'user_id': ObjectId(user_id)})
    
    if result.deleted_count == 0:
        return jsonify({'error': 'Todo not found'}), 404
    
    return jsonify({'message': 'Todo deleted successfully'})

# POST /api/timetable - create or update timetable entry
@bp.route('/api/timetable', methods=['POST'])
@jwt_required()
def create_timetable_entry():
    user_id = get_jwt_identity()
    data = request.get_json()
    day = data.get('day')  # monday, tuesday, etc.
    start_time = data.get('start_time')  # 09:00, 10:00, etc.
    end_time = data.get('end_time')  # 10:00, 11:00, etc.
    activity = data.get('activity')
    color = data.get('color', '#3B82F6')  # default blue
    
    if not all([day, start_time, end_time, activity]):
        return jsonify({'error': 'Day, start_time, end_time, and activity are required'}), 400
    
    # Check if entry already exists for this day and time range
    existing = timetables.find_one({
        'user_id': ObjectId(user_id),
        'day': day,
        'start_time': start_time,
        'end_time': end_time
    })
    
    if existing:
        # Update existing entry
        result = timetables.update_one(
            {'_id': existing['_id']},
            {'$set': {'activity': activity, 'color': color}}
        )
        message = 'Timetable entry updated successfully'
    else:
        # Create new entry
        entry = {
            'user_id': ObjectId(user_id),
            'day': day,
            'start_time': start_time,
            'end_time': end_time,
            'activity': activity,
            'color': color,
            'created_at': datetime.now()
        }
        timetables.insert_one(entry)
        message = 'Timetable entry created successfully'
    
    return jsonify({'message': message})

# GET /api/timetable - get all timetable entries for user
@bp.route('/api/timetable', methods=['GET'])
@jwt_required()
def get_timetable():
    user_id = get_jwt_identity()
    entries = list(timetables.find({'user_id': ObjectId(user_id)}).sort('day', 1).sort('start_time', 1))
    
    for entry in entries:
        entry['id'] = str(entry['_id'])
        entry['created_at'] = entry['created_at'].isoformat()
        del entry['_id']
        del entry['user_id']
    
    return jsonify(entries)

# DELETE /api/timetable/<id> - delete a timetable entry
@bp.route('/api/timetable/<entry_id>', methods=['DELETE'])
@jwt_required()
def delete_timetable_entry(entry_id):
    user_id = get_jwt_identity()
    result = timetables.delete_one({'_id': ObjectId(entry_id), 'user_id': ObjectId(user_id)})
    
    if result.deleted_count == 0:
        return jsonify({'error': 'Timetable entry not found'}), 404
    
    return jsonify({'message': 'Timetable entry deleted successfully'})

# GET /api/timetable/week - get weekly timetable view
@bp.route('/api/timetable/week', methods=['GET'])
@jwt_required()
def get_weekly_timetable():
    user_id = get_jwt_identity()
    entries = list(timetables.find({'user_id': ObjectId(user_id)}).sort('day', 1).sort('start_time', 1))
    
    # Organize by day
    weekly_data = {
        'monday': [],
        'tuesday': [],
        'wednesday': [],
        'thursday': [],
        'friday': [],
        'saturday': [],
        'sunday': []
    }
    
    for entry in entries:
        entry['id'] = str(entry['_id'])
        entry['created_at'] = entry['created_at'].isoformat()
        del entry['_id']
        del entry['user_id']
        weekly_data[entry['day']].append(entry)
    
    return jsonify(weekly_data) 