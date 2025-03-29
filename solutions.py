import logging
import sympy as sp
from flask import Blueprint, request, jsonify
from models import db, Task, Solution, Step
from checker import safe_sympify  # функции проверки из checker.py

solutions_bp = Blueprint('solutions', __name__, url_prefix='/api/solutions')

@solutions_bp.route('/check', methods=['POST'])
def check_solution():
    """
    Проверяет полное решение (с шагами) студента и сохраняет его в БД.
    Ожидается JSON вида:
    {
        "taskId": <идентификатор задачи>,
        "steps": [
            "шаг 1", "шаг 2", ..., "LIMIT", "окончательный ответ"
        ]
    }
    Если ошибок нет – возвращает success: true, иначе success: false с описанием ошибок.
    """
    data = request.json
    logging.info("Получен запрос на проверку решения: %s", data)

    if not data or "taskId" not in data or "steps" not in data:
        return jsonify({"error": "Неверный формат запроса"}), 400

    task_id = data["taskId"]
    steps = data["steps"]

    if not isinstance(steps, list) or any(not isinstance(s, str) for s in steps):
        return jsonify({"error": "steps должен быть массивом строк"}), 400

    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Задача не найдена"}), 404

    x = sp.Symbol('x')
    errors = []  # соберем ошибки по шагам
    algebraic_steps = []
    found_limit = False

    for step in steps:
        if step == "LIMIT":
            found_limit = True
            break
        algebraic_steps.append(step)

    if not algebraic_steps:
        return jsonify({
            "success": False,
            "errors": [{"step": 1, "error": "Нет алгебраических шагов", "hint": "Добавьте хотя бы один шаг"}]
        }), 200

    # Проверка последовательных алгебраических шагов
    for i in range(len(algebraic_steps) - 1):
        prev_expr = algebraic_steps[i]
        curr_expr = algebraic_steps[i + 1]
        try:
            prev_sym = sp.simplify(safe_sympify(prev_expr))
            curr_sym = sp.simplify(safe_sympify(curr_expr))
            if not prev_sym.equals(curr_sym):
                errors.append({
                    "step": i + 1,
                    "error": "Некорректное преобразование",
                    "expected": str(prev_sym),
                    "received": str(curr_sym),
                    "hint": f"Допустимая эквивалентная форма: {prev_sym}"
                })
        except Exception as e:
            errors.append({
                "step": i + 1,
                "error": "Ошибка в выражении",
                "details": str(e),
                "hint": "Проверьте правильность записи"
            })

    computed_limit = None
    # Если найден маркер LIMIT – проверяем предел
    if found_limit:
        try:
            last_expr = sp.simplify(safe_sympify(algebraic_steps[-1]))
            computed_limit = sp.limit(last_expr, x, sp.oo)
            expected_limit = sp.simplify(safe_sympify(task.expected_limit))
            logging.info(f"Вычисленный предел: {computed_limit}")
            if not sp.simplify(computed_limit - expected_limit).is_zero:
                errors.append({
                    "step": len(steps),
                    "error": "Неверный предел",
                    "expected": str(expected_limit),
                    "received": str(computed_limit),
                    "hint": f"Ожидаемый результат: {expected_limit}"
                })
            # Если последний шаг не равен "LIMIT" и ошибок нет – сравниваем окончательный ответ
            if steps[-1] != "LIMIT" and not errors:
                student_result = sp.simplify(safe_sympify(steps[-1]))
                if not sp.simplify(student_result - computed_limit).is_zero:
                    errors.append({
                        "step": len(steps),
                        "error": "Некорректный окончательный ответ",
                        "expected": str(computed_limit),
                        "received": str(student_result),
                        "hint": f"После 'LIMIT' результат должен быть: {computed_limit}"
                    })
        except Exception as e:
            logging.error(f"Ошибка вычисления предела: {str(e)}")
            errors.append({
                "step": len(steps),
                "error": "Ошибка предельного перехода",
                "details": str(e),
                "hint": "Проверьте выражение перед LIMIT"
            })

    # Создаем запись решения (замените user_id на актуальный, например, из сессии)
    solution = Solution(task_id=task.id, user_id=1, status="in_progress")
    db.session.add(solution)
    db.session.commit()

    # Сохраняем каждый шаг решения в таблице Step
    for i, step in enumerate(steps, start=1):
        # Если для данного шага есть ошибка, её можно передать из errors (если таковая найдена для этого шага)
        # Здесь для упрощения: если глобальные ошибки обнаружены – все шаги считаются некорректными
        is_correct = False if errors else True
        new_step = Step(
            solution_id=solution.id,
            step_number=i,
            input_expr=step,
            is_correct=is_correct,
            error_type=None if is_correct else "ошибка",  # Можно дополнить более детально
            hint=""
        )
        db.session.add(new_step)
    db.session.commit()

    if errors:
        solution.status = "error"
        db.session.commit()
        return jsonify({"success": False, "errors": errors, "solution_id": solution.id}), 200

    solution.status = "completed"
    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"Решение верное. Предел = {computed_limit}" if computed_limit is not None else "Решение верное",
        "solution_id": solution.id
    }), 200
