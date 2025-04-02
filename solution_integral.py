import logging
import sympy as sp
from flask import Blueprint, request, jsonify
from models import db, Task, Solution, Step
from flask_cors import cross_origin
from latex2sympy2 import latex2sympy  # Преобразование LaTeX в Sympy
from typing import List
import re

solution_integral_bp = Blueprint('solution_integral', __name__, url_prefix='/api/solutions')

def safe_sympify(expr):
    """Безопасно преобразует LaTeX-выражение в объект sympy, используя latex2sympy2."""
    print(f"Parsed expression: {expr}")
    try:
        
        sympy_expr = latex2sympy(expr)
        
        return sympy_expr
    except Exception as e:
        logging.error(f"Expression parsing error: '{expr}' - {str(e)}")
        raise ValueError(f"Cannot parse expression '{expr}': {str(e)}")

def check_algebraic_step(prev_expr_str, curr_expr_str, tolerance=1e-10):
    """
    Проверяет, корректно ли выполнено алгебраическое преобразование между двумя шагами.
    Если один из шагов равен "LIMIT", проверка пропускается.
    """
    try:
        if prev_expr_str.strip().upper() == "LIMIT" or curr_expr_str.strip().upper() == "LIMIT":
            return {"is_correct": True, "error_type": None, "hint": None}
        prev_expr = sp.simplify(safe_sympify(prev_expr_str))
        curr_expr = sp.simplify(safe_sympify(curr_expr_str))
        if prev_expr.equals(curr_expr):
            return {"is_correct": True, "error_type": None, "hint": None}
        x = sp.Symbol('x')
        test_values = [1, 2, 3, 5, 10, 100]
        for val in test_values:
            try:
                prev_val = float(prev_expr.subs({x: val}))
                curr_val = float(curr_expr.subs({x: val}))
                if not (sp.isinf(prev_val) or sp.isinf(curr_val) or sp.isnan(prev_val) or sp.isnan(curr_val)):
                    if abs(prev_val - curr_val) > tolerance:
                        return {
                            "is_correct": False,
                            "error_type": "algebraic_error",
                            "hint": f"Для x={val}: предыдущее = {prev_val:.6f}, текущее = {curr_val:.6f}"
                        }
            except Exception:
                continue
        return {"is_correct": True, "error_type": None, "hint": None}
    except Exception as e:
        logging.error(f"Error checking step: {str(e)}")
        return {"is_correct": False, "error_type": "parse_error", "hint": f"Ошибка: {str(e)}"}

def check_integral_solution_final(final_solution_str, integrand_str, var_str="x"):
    """
    Проверяет окончательный ответ по интегралу.
    Дифференцирует конечное выражение и сравнивает его с интегрантом.
    """
    try:
        final_expr = sp.simplify(safe_sympify(final_solution_str))
        integrand_expr = sp.simplify(safe_sympify(integrand_str))
        var = sp.Symbol(var_str)
        
        diff_expr = sp.simplify(final_expr - integrand_expr)
        # Если разность равна нулю или является числом (возможно, константой), считаем шаг корректным
        if diff_expr == 0 or diff_expr.is_number:
            return {"is_correct": True, "error_type": None, "hint": None}
        else:
            return {
                "is_correct": False,
                "error_type": "integral_error",
                "hint": f"Производная вашего ответа равна {sp.pretty(final_expr)}, а интегрант — {sp.pretty(integrand_expr)}"
            }
    except Exception as e:
        logging.error(f"Error checking integral solution: {str(e)}")
        return {"is_correct": False, "error_type": "parse_error", "hint": f"Ошибка проверки: {str(e)}"}

@solution_integral_bp.route('/check-integral', methods=['POST'])
@cross_origin()
def check_integral_solution():
    """
    Проверяет решение интегральной задачи.
    Ожидаемый формат JSON:
    {
        "taskId": <task_id>,
        "phiSteps": [
            {
                "label": "\\varphi_0(x)",
                "steps": ["шаг 1", "шаг 2", ...]
            },
            { ... }  // возможно, несколько φ-функций
        ],
        "finalSolution": "LaTeX строки с окончательным ответом"
    }
    """
    data = request.json
    logging.info(f"Received integral solution check request: {data}")

    # Валидация входных данных
    if not data or "taskId" not in data or "phiSteps" not in data or "finalSolution" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    task_id = data["taskId"]
    phi_steps = data["phiSteps"]
    final_solution = data["finalSolution"]

    if not isinstance(phi_steps, list) or len(phi_steps) < 1:
        return jsonify({
            "success": False,
            "errors": [{"phiIndex": 0, "error": "Должна быть хотя бы одна φ-функция с шагами"}]
        }), 400

    # Получаем задачу из БД (ожидается, что для интегральных задач в модели поле integrand хранится, например, в task.equation)
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    errors = []  # Список ошибок для φ-функций и окончательного ответа

    # Проверка последовательности шагов для каждой φ-функции
    for phi_index, phi in enumerate(phi_steps):
        steps = phi.get("steps")
        if not isinstance(steps, list) or len(steps) < 1:
            errors.append({
                "phiIndex": phi_index,
                "error": "Функция должна содержать хотя бы один шаг",
                "hint": "Заполните шаги для данной φ-функции"
            })
            continue
        # Если больше одного шага – проверяем корректность последовательных преобразований
        if len(steps) > 1:
            for i in range(len(steps) - 1):
                result = check_algebraic_step(steps[i], steps[i + 1])
                if not result["is_correct"]:
                    errors.append({
                        "phiIndex": phi_index,
                        "stepIndex": i + 1,
                        "error": "Некорректное преобразование",
                        "hint": result["hint"] or "Проверьте шаги"
                    })

    # Проверка окончательного ответа по интегралу.
    # Предполагается, что в задаче для интегральных задач хранится интегрант в поле task.equation
    if not final_solution.strip():
        errors.append({
            "phiIndex": -1,
            "error": "Окончательный ответ отсутствует",
            "hint": "Введите окончательный ответ по интегралу"
        })
    else:
        integral_check = check_integral_solution_final(final_solution, task.expected_value, var_str="x")
        if not integral_check["is_correct"]:
            errors.append({
                "phiIndex": -1,
                "error": "Неверный окончательный ответ",
                "hint": integral_check["hint"]
            })

    # Создаем запись решения (user_id — заглушка)
    user_id = 1
    solution = Solution(task_id=task.id, user_id=user_id, status="in_progress")
    db.session.add(solution)
    db.session.flush()  # Для получения solution.id без коммита

    # Сохраняем шаги решения: сохраняем каждый шаг каждой φ-функции, затем окончательный ответ
    step_counter = 1
    for phi in phi_steps:
        steps = phi.get("steps", [])
        for step in steps:
            step_record = Step(
                solution_id=solution.id,
                step_number=step_counter,
                input_expr=step,
                is_correct=(len(errors) == 0),
                error_type=None if len(errors) == 0 else "error",
                hint=""
            )
            db.session.add(step_record)
            step_counter += 1
    # Сохраняем окончательный ответ как последний шаг
    final_step_record = Step(
        solution_id=solution.id,
        step_number=step_counter,
        input_expr=final_solution,
        is_correct=(len(errors) == 0),
        error_type=None if len(errors) == 0 else "error",
        hint=""
    )
    db.session.add(final_step_record)

    # Обновляем статус решения
    solution.status = "completed" if not errors else "error"
    db.session.commit()

    if errors:
        return jsonify({
            "success": False,
            "errors": errors,
            "solution_id": solution.id
        })
    return jsonify({
        "success": True,
        "message": "Решение верное.",
        "solution_id": solution.id
    })
