from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List, Dict
import os  # Import the os module

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this to a strong, random key in production
CORS(app)

# Determine the database file path
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'tasks.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable track modifications

db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# Task model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    deadline = db.Column(db.String(10), nullable=False)
    urgency_score = db.Column(db.Integer, nullable=False, default=5)
    normalized_urgency = db.Column(db.Float, nullable=False, default=0.5)
    dependencies = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    ml_priority_score = db.Column(db.Float, nullable=True)

def format_dependencies(deps_str: str) -> List[int]:
    if not deps_str:
        return []
    return [int(d) for d in deps_str.split(',') if d]

def serialize_task(task: Task) -> Dict:
    return {
        'id': task.id,
        'name': task.name,
        'deadline': task.deadline,
        'urgency_score': task.urgency_score,
        'normalized_urgency': task.normalized_urgency,
        'dependencies': format_dependencies(task.dependencies),
        'status': task.status,
        'ml_priority_score': task.ml_priority_score
    }

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error_message="Username already exists.")

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"User registered: {username}")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.username
            logger.info(f"User logged in: {username}")
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f"Failed login attempt for user: {username}")
            return render_template('login.html', error_message="Invalid credentials.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_name = session.get('user_name')
    return render_template('dashboard.html', user=user_name)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('login'))

@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'GET':
        tasks = Task.query.all()
        return jsonify([serialize_task(t) for t in tasks])
    elif request.method == 'POST':
        data = request.json
        dependencies = ','.join(map(str, data.get('dependencies', [])))
        try:
            task = Task(
                name=data['name'],
                deadline=data['deadline'],
                urgency_score=data.get('urgency_score', 5),
                normalized_urgency=data.get('normalized_urgency', 0.5),
                dependencies=dependencies
            )
            db.session.add(task)
            db.session.commit()
            return jsonify(serialize_task(task)), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating task: {e}")
            return jsonify({'error': 'Failed to create task'}), 500

@app.route('/tasks/<int:task_id>', methods=['PUT', 'DELETE'])
def update_delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task = Task.query.get_or_404(task_id)
    try:
        if request.method == 'PUT':
            data = request.json
            task.name = data['name']
            task.deadline = data['deadline']
            task.urgency_score = data.get('urgency_score', task.urgency_score)
            task.normalized_urgency = data.get('normalized_urgency', task.normalized_urgency)
            task.dependencies = ','.join(map(str, data.get('dependencies', [])))
            task.status = data.get('status', task.status)
            db.session.commit()
            return jsonify(serialize_task(task))
        else:  # DELETE
            db.session.delete(task)
            db.session.commit()
            return jsonify({'message': 'Task deleted'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating/deleting task {task_id}: {e}")
        return jsonify({'error': f'Failed to update/delete task {task_id}'}), 500

from task_logic import prioritize_tasks, MODEL_LOAD_FAILED  # Import the function AND the flag

@app.route('/tasks/prioritize', methods=['POST'])
def prioritize_tasks_endpoint():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    completed_ids = request.json.get('completed_ids', [])
    logger.info(f"Completed IDs: {completed_ids}")

    tasks = Task.query.all()
    task_list = [serialize_task(t) for t in tasks]
    logger.info(f"Task List: {task_list}")

    #  CRITICAL: Check if the model failed to load!
    if MODEL_LOAD_FAILED:
        logger.error("Model failed to load. Prioritization is unavailable.")
        return jsonify({'error': 'Model failed to load. Prioritization is unavailable.'}), 500

    try:
        prioritized_tasks: List[Dict] = prioritize_tasks(task_list, completed_ids)
        for p_task in prioritized_tasks:
            if p_task['id'] is not None:  # Check if the task id is valid
                task = Task.query.get(p_task['id'])  # Get the task from the database
                if task:
                    task.ml_priority_score = p_task['score']  # Assign the score.
                    db.session.commit()
                else:
                    logger.warning(f"Task with id {p_task['id']} not found.")

        db.session.commit()
        logger.info(f"Prioritized Tasks: {prioritized_tasks}")
        return jsonify(prioritized_tasks)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during prioritization: {e}")
        return jsonify({'error': f'Failed to prioritize tasks: {e}'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables within the app context
    app.run(debug=True)