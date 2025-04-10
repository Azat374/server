import logging
import re
import sympy as sp
from flask import Blueprint, request, jsonify, send_file
from flask_cors import cross_origin
from latex2sympy2 import latex2sympy  # Преобразование LaTeX в sympy-выражения
from models import db, Task, Solution, Step
from typing import List

solutions_bp = Blueprint('solutions', __name__, url_prefix='/api/solutions')

def normalize_steps_with_limit(steps: List[str]) -> List[str]:
    # Если хотя бы один шаг содержит "\lim", возвращаем шаги без изменений
    if any("\\lim" in step for step in steps):
        logging.info("Обнаружен шаг с '\\lim', не добавляем маркер LIMIT.")
        return steps
    else:
        # Если отсутствуют лимитные шаги и шагов >= 2, вставляем маркер "LIMIT" (например, в середину)
        if len(steps) >= 2:
            mid = len(steps) // 2
            steps.insert(mid, "LIMIT")
        return steps

def safe_sympify(expr: str):
    """
    Преобразует LaTeX-выражение в символьное выражение sympy.
    Если выражение начинается с '\\lim', то выделяет компоненты и вычисляет предел явно.
    Теперь не удаляет фрагменты, а пытается корректно разобрать выражение даже если в конце есть комментарий.
    """
    try:
        expr_strip = expr.strip()
        if expr_strip.upper() == "LIMIT":
            return sp.Integer(0)
        # Если выражение начинается с \lim, пытаемся его разобрать
        if expr_strip.startswith("\\lim"):
            # Используем регулярное выражение, которое берёт всё от \lim_{...} до первой закрывающей пары скобок после \right)
            pattern = re.compile(r"\\lim_\{([^}]+)\\to\s*([^}]+)\}(.*)")
            m = pattern.search(expr_strip)
            if m:
                var_str = m.group(1).strip()
                limit_val_str = m.group(2).strip()
                rest = m.group(3).strip()
                # Если во второй части есть лишние символы (например, комментарий),
                # попробуем выделить содержимое от \left( до \right)
                start = rest.find("\\left(")
                end = rest.rfind("\\right)")
                if start != -1 and end != -1 and end > start:
                    inner_expr_str = rest[start:end+len("\\right)")]
                else:
                    # Если нет обрамляющих конструкций, берем весь оставшийся текст
                    inner_expr_str = rest
                var = sp.Symbol(var_str)
                # Определяем точку предела
                if limit_val_str in ["∞", "infty", "infinity"]:
                    limit_val = sp.oo
                elif limit_val_str in ["-∞", "-infty", "-infinity"]:
                    limit_val = -sp.oo
                else:
                    # Пробуем вычислить как число/выражение
                    limit_val = safe_sympify(limit_val_str)
                # Преобразуем внутреннее выражение
                inner_expr = latex2sympy(inner_expr_str)
                computed_limit = sp.limit(inner_expr, var, limit_val)
                logging.info(f"Вычислен предел для {expr_strip}: {computed_limit}")
                return computed_limit
            else:
                # Если шаблон не подошёл, пытаемся обычное преобразование
                return latex2sympy(expr_strip)
        # Для остальных выражений – обычное преобразование
        return latex2sympy(expr_strip)
    except Exception as e:
        logging.error(f"Expression parsing error: '{expr}' - {str(e)}")
        raise ValueError(f"Cannot parse expression '{expr}': {str(e)}")

def check_algebraic_step(prev_expr_str: str, curr_expr_str: str, tolerance=1e-6):
    """
    Проверяет корректность алгебраического преобразования между двумя шагами.
    Если оба шага начинаются с \lim — сначала сравниваются внутренние части лимита.
    Затем выполняется обычная символьная и численная проверка.
    """
    try:
        if prev_expr_str.strip().upper() == "LIMIT" or curr_expr_str.strip().upper() == "LIMIT":
            return {"is_correct": True, "error_type": None, "hint": None}

        # Проверка: оба шага — лимитные выражения
        if prev_expr_str.strip().startswith("\\lim") and curr_expr_str.strip().startswith("\\lim"):
            lim_pattern = re.compile(r"\\lim_\{[^}]+\}(.*)")

            prev_match = lim_pattern.search(prev_expr_str)
            curr_match = lim_pattern.search(curr_expr_str)

            if prev_match and curr_match:
                prev_inner = prev_match.group(1).strip()
                curr_inner = curr_match.group(1).strip()

                prev_inner_expr = sp.simplify(safe_sympify(prev_inner))
                curr_inner_expr = sp.simplify(safe_sympify(curr_inner))

                if sp.simplify(prev_inner_expr - curr_inner_expr) == 0:
                    return {"is_correct": True, "error_type": None, "hint": None}

                # Проверка по точкам
                x = sp.Symbol("x")
                test_values = [2, 5, 10, 50, 100]
                for val in test_values:
                    try:
                        prev_val = float(prev_inner_expr.evalf(subs={x: val}))
                        curr_val = float(curr_inner_expr.evalf(subs={x: val}))
                        if abs(prev_val - curr_val) > tolerance:
                            return {
                                "is_correct": False,
                                "error_type": "algebraic_error",
                                "hint": f"(внутри предела) при x={val}: было {prev_val:.6f}, стало {curr_val:.6f}"
                            }
                    except Exception as e:
                        logging.warning(f"Inner limit eval error: {e}")
                        continue

        # Обычная проверка всего выражения
        prev_expr = sp.simplify(safe_sympify(prev_expr_str))
        curr_expr = sp.simplify(safe_sympify(curr_expr_str))

        if sp.simplify(prev_expr - curr_expr) == 0:
            return {"is_correct": True, "error_type": None, "hint": None}

        # Проверка по численным значениям
        x = sp.Symbol('x')
        test_values = [2, 5, 10, 50, 100]
        for val in test_values:
            try:
                prev_val = float(prev_expr.evalf(subs={x: val}))
                curr_val = float(curr_expr.evalf(subs={x: val}))
                if abs(prev_val - curr_val) > tolerance:
                    return {
                        "is_correct": False,
                        "error_type": "algebraic_error",
                        "hint": f"Ошибка внутри предела: при x={val}: было {prev_val:.6f}, стало {curr_val:.6f}"
                    }
            except Exception as e:
                logging.warning(f"Outer eval error: {e}")
                continue

        return {"is_correct": True, "error_type": None, "hint": None}

    except Exception as e:
        logging.error(f"Ошибка при проверке шага: {str(e)}")
        return {"is_correct": False, "error_type": "parse_error", "hint": str(e)}

def check_limit(expr_str: str, var_str: str, limit_point: str):
    """
    Вычисляет предел выражения expr_str для переменной var_str при стремлении к limit_point.
    """
    try:
        expr = safe_sympify(expr_str)
        var = sp.Symbol(var_str)
        if limit_point in ["oo", "∞", "infty", "infinity"]:
            limit_result = sp.limit(expr, var, sp.oo)
        elif limit_point in ["-oo", "-∞", "-infty", "-infinity"]:
            limit_result = sp.limit(expr, var, -sp.oo)
        else:
            limit_result = sp.limit(expr, var, limit_point)
        logging.info(f"Computed limit for '{expr_str}': {limit_result}")
        return {"is_correct": True, "computed_limit": limit_result, "error_type": None, "hint": None}
    except Exception as e:
        logging.error(f"Error computing limit: {str(e)}")
        return {"is_correct": False, "computed_limit": None, "error_type": "limit_error", "hint": f"Ошибка при вычислении предела: {str(e)}"}

def compare_limit_values(student_result, expected_result):
    """
    Сравнивает результат предела, полученный студентом, с вычисленным значением.
    Возвращает True, если значения совпадают (учитывая бесконечности), иначе False.
    """
    try:
        if (student_result == sp.oo and expected_result == sp.oo) or (student_result == -sp.oo and expected_result == -sp.oo):
            return True
        diff = sp.simplify(student_result - expected_result)
        return diff == 0
    except Exception:
        return str(student_result) == str(expected_result)

@solutions_bp.route('/check/limit', methods=['POST'])
@cross_origin()
def check_solution():
    """
    Принимает JSON:
    {
        "taskId": <номер задачи>,
        "steps": [
            "шаг 1", "шаг 2", ..., "LIMIT", "окончательный ответ"
        ]
    }
    Выполняет пошаговую проверку: 
    - Последовательность алгебраических преобразований.
    - Вычисление лимита на основе последнего алгебраического шага.
    - Сравнение окончательного ответа со значением лимита.
    """
    data = request.json
    logging.info(f"Received solution check request: {data}")

    if not data or "taskId" not in data or "steps" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    task_id = data["taskId"]
    steps_raw = data["steps"]
    logging.info(f"Received steps: {steps_raw}")

    if not isinstance(steps_raw, list) or len(steps_raw) < 2:
        return jsonify({
            "success": False,
            "errors": [{"step": 1, "error": "Решение должно состоять как минимум из двух шагов"}]
        }), 400

    # Если среди поступивших шагов нет ни одного содержащего "\lim", вставляем маркер "LIMIT"
    steps = normalize_steps_with_limit(steps_raw)
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    errors = []
    algebraic_steps = []
    found_limit = False
    limit_index = -1

    # Определяем алгебраические шаги (до маркера "LIMIT", если он вставлен)
    for i, step in enumerate(steps):
        if step.strip().upper() == "LIMIT":
            found_limit = True
            limit_index = i
            break
        algebraic_steps.append(step)

    if not algebraic_steps:
        return jsonify({
            "success": False,
            "errors": [{"step": 1, "error": "Алгебраические шаги отсутствуют", "hint": "Добавьте хотя бы один шаг перед LIMIT"}]
        }), 200

    # Проверка последовательности алгебраических шагов
    for i in range(len(algebraic_steps) - 1):
        res = check_algebraic_step(algebraic_steps[i], algebraic_steps[i + 1])
        if not res["is_correct"]:
            errors.append({
                "step": i + 2,
                "error": "Некорректное преобразование",
                "hint": res["hint"] or "Проверьте алгебраические преобразования"
            })

    computed_limit = None
    if found_limit and not errors:
        try:
            # Для вычисления предела используем последний алгебраический шаг
            last_expr = algebraic_steps[-1]
            # Определяем переменную и точку предела на основе task.limitVar (например, "x→oo")
            limit_var = "x"  # значение по умолчанию
            limit_point = "oo"
            if task.limitVar:
                parts = task.limitVar.split("→")
                if len(parts) == 2:
                    limit_var = parts[0].strip()
                    limit_point = parts[1].strip()
            limit_res = check_limit(last_expr, limit_var, limit_point)
            computed_limit = limit_res.get("computed_limit")
            if not limit_res["is_correct"]:
                errors.append({
                    "step": limit_index + 1,
                    "error": "Ошибка при вычислении предела",
                    "hint": limit_res["hint"]
                })
            # Если после вставленного маркера LIMIT указан окончательный ответ – сравниваем его с вычисленным пределом
            if limit_index < len(steps) - 1 and not errors:
                student_answer = steps[-1]
                try:
                    if student_answer.strip() in ["\\infty", "\\infinity", "∞"]:
                        student_result = sp.oo
                    elif student_answer.strip() in ["-\\infty", "-\\infinity", "-∞"]:
                        student_result = -sp.oo
                    else:
                        student_result = sp.simplify(safe_sympify(student_answer))
                    if not compare_limit_values(student_result, computed_limit):
                        errors.append({
                            "step": len(steps),
                            "error": "Некорректный окончательный ответ",
                            "hint": f"Итоговое выражение должно равняться {computed_limit}"
                        })
                except Exception as e:
                    errors.append({
                        "step": len(steps),
                        "error": "Ошибка в анализе окончательного ответа",
                        "hint": f"Ошибка: {str(e)}"
                    })
        except Exception as e:
            logging.error(f"Limit calculation error: {str(e)}")
            errors.append({
                "step": limit_index + 1,
                "error": "Ошибка при обработке предела",
                "hint": str(e)
            })

    # Сохраняем решение и шаги в базу
    user_id = 1  # Заглушка для пользователя
    solution = Solution(task_id=task.id, user_id=user_id, status="in_progress")
    db.session.add(solution)
    db.session.flush()

    for i, step in enumerate(steps, start=1):
        is_correct = (len(errors) == 0)
        step_record = Step(
            solution_id=solution.id,
            step_number=i,
            input_expr=step,
            is_correct=is_correct,
            error_type=None if is_correct else "error",
            hint=""
        )
        db.session.add(step_record)

    solution.status = "completed" if not errors else "error"
    db.session.commit()

    if errors:
        return jsonify({"success": False, "errors": errors, "solution_id": solution.id}), 200

    return jsonify({
        "success": True,
        "message": f"Решение верное. Предел = {computed_limit}" if computed_limit is not None else "Решение верное",
        "solution_id": solution.id
    }), 200



@solutions_bp.route('/last/<int:task_id>', methods=['GET'])
@cross_origin()
def get_last_solution(task_id):
    solution = Solution.query.filter_by(task_id=task_id).order_by(Solution.created_at.desc()).first()
    
    if not solution:
        return jsonify({"latex": ""})

    steps = Step.query.filter_by(solution_id=solution.id).order_by(Step.step_number).all()
    latex_expr = " = ".join(step.input_expr for step in steps)
    return jsonify({"latex": latex_expr})


@solutions_bp.route('/check/integral', methods=['POST'])
@cross_origin()
def check_integral():
    data = request.json
    if not data or "taskId" not in data or "steps" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    task = Task.query.get(data["taskId"])
    if not task:
        return jsonify({"error": "Task not found"}), 404

    steps = data["steps"]
    errors = []

    try:
        # Предполагаем, что последний шаг — результат интегрирования
        expected = sp.simplify(latex2sympy(task.expected_value))
        student = sp.simplify(latex2sympy(steps[-1]))

        if not sp.simplify(expected - student) == 0:
            errors.append({
                "step": len(steps),
                "error": "Неверный результат интегрирования",
                "hint": f"Ожидается: {task.expected_value}"
            })

    except Exception as e:
        errors.append({
            "step": len(steps),
            "error": "Ошибка разбора",
            "hint": str(e)
        })

    solution = Solution(task_id=task.id, user_id=1, status="completed" if not errors else "error")
    db.session.add(solution)
    db.session.flush()

    for i, step in enumerate(steps):
        db.session.add(Step(
            solution_id=solution.id,
            step_number=i + 1,
            input_expr=step,
            is_correct=(len(errors) == 0),
            error_type=None if len(errors) == 0 else "error",
            hint=""
        ))

    db.session.commit()

    if errors:
        return jsonify({"success": False, "errors": errors, "solution_id": solution.id}), 200

    return jsonify({"success": True, "message": "Решение верное", "solution_id": solution.id}), 200


@solutions_bp.route('/check/algebra', methods=['POST'])
@cross_origin()
def check_algebra():
    data = request.json
    if not data or "taskId" not in data or "steps" not in data:
        return jsonify({"error": "Invalid request format"}), 400

    task = Task.query.get(data["taskId"])
    if not task:
        return jsonify({"error": "Task not found"}), 404

    steps = data["steps"]
    errors = []

    try:
        for i in range(len(steps) - 1):
            lhs = sp.simplify(latex2sympy(steps[i]))
            rhs = sp.simplify(latex2sympy(steps[i + 1]))

            if not sp.simplify(lhs - rhs) == 0:
                errors.append({
                    "step": i + 2,
                    "error": "Неверное преобразование",
                    "hint": f"Шаг {i + 2} отличается от предыдущего"
                })
    except Exception as e:
        errors.append({
            "step": len(steps),
            "error": "Ошибка разбора выражения",
            "hint": str(e)
        })

    solution = Solution(task_id=task.id, user_id=1, status="completed" if not errors else "error")
    db.session.add(solution)
    db.session.flush()

    for i, step in enumerate(steps):
        db.session.add(Step(
            solution_id=solution.id,
            step_number=i + 1,
            input_expr=step,
            is_correct=(len(errors) == 0),
            error_type=None if len(errors) == 0 else "error",
            hint=""
        ))

    db.session.commit()

    if errors:
        return jsonify({"success": False, "errors": errors, "solution_id": solution.id}), 200

    return jsonify({"success": True, "message": "Решение верное", "solution_id": solution.id}), 200
