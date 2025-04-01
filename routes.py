from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Task, Solution, Step
from checker import check_step
from utils.Auth.auth import signup_handler, signin_handler
import cloudinary
import cloudinary.uploader
from models import User

app = Flask(__name__)
app.config.from_object("config.Config")
db.init_app(app)
CORS(app)

@app.route("/tasks", methods=["GET"])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([{"id": t.id, "title": t.title, "description": t.description, "category": t.category} for t in tasks])

@app.route("/tasks/<int:task_id>/start", methods=["POST"])
def start_solution(task_id):
    solution = Solution(task_id=task_id, status="in_progress")
    db.session.add(solution)
    db.session.commit()
    return jsonify({"solution_id": solution.id})

@app.route("/solutions/<int:solution_id>/check_step", methods=["POST"])
def check_solution_step(solution_id):
    data = request.json
    step_number = data.get("step_number")
    prev_expr = data.get("prev_expr", "")
    curr_expr = data.get("curr_expr", "")

    result = check_step(prev_expr, curr_expr)
    
    step = Step(solution_id=solution_id, step_number=step_number,
                input_expr=curr_expr, is_correct=result["is_correct"],
                error_type=result["error_type"], hint=result["hint"])
    
    db.session.add(step)
    db.session.commit()

    return jsonify(result)

@app.route("/solutions/<int:solution_id>/finish", methods=["POST"])
def finish_solution(solution_id):
    solution = Solution.query.get(solution_id)
    solution.status = "completed"
    db.session.commit()
    return jsonify({"message": "Решение завершено!"})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

