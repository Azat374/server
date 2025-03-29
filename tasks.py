from flask import Blueprint, request, jsonify
from models import db, Task

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@tasks_bp.route('', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    tasks_list = []
    for t in tasks:
        tasks_list.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "expression": t.expression,
            "limitVar": t.limitVar,
            "expected_limit": t.expected_limit
        })
    return jsonify({"tasks": tasks_list}), 200

@tasks_bp.route('/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """
    Добавленный эндпоинт для получения одной задачи по ID.
    """
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404
    return jsonify({
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "expression": task.expression,
        "limitVar": task.limitVar,
        "expected_limit": task.expected_limit
    }), 200

@tasks_bp.route('', methods=['POST'])
def create_task():
    data = request.json
    required_fields = ['title', 'expression', 'limitVar', 'expected_limit']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"{field} is required"}), 400

    new_task = Task(
        title=data['title'],
        description=data.get('description', ''),
        expression=data['expression'],
        limitVar=data['limitVar'],
        expected_limit=data['expected_limit']
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify({"message": "Task created successfully", "task_id": new_task.id}), 201

@tasks_bp.route('/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404
    data = request.json
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.expression = data.get('expression', task.expression)
    task.limitVar = data.get('limitVar', task.limitVar)
    task.expected_limit = data.get('expected_limit', task.expected_limit)
    db.session.commit()
    return jsonify({"message": "Task updated successfully"}), 200

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted successfully"}), 200
