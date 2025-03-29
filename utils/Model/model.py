from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.Text, default="")
    image = db.Column(db.String(300), default="")
    role = db.Column(db.String(50), default="student")  # или "admin"
    chat_history = db.Column(db.Text)  # можно хранить JSON как строку

    solutions = db.relationship('Solution', backref='user', lazy=True)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    expression = db.Column(db.String(500), nullable=False)  # исходное математическое выражение
    limitVar = db.Column(db.String(50), nullable=False)      # например "x->∞"
    expected_limit = db.Column(db.String(100), nullable=False)

    solutions = db.relationship('Solution', backref='task', lazy=True)

class Solution(db.Model):
    __tablename__ = 'solutions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    status = db.Column(db.String(50), default="in_progress")  # in_progress, completed, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    steps = db.relationship('Step', backref='solution', lazy=True)

class Step(db.Model):
    __tablename__ = 'steps'
    id = db.Column(db.Integer, primary_key=True)
    solution_id = db.Column(db.Integer, db.ForeignKey('solutions.id'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    input_expr = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=True)
    error_type = db.Column(db.String(100))
    hint = db.Column(db.String(300))
