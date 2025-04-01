import logging
import sympy as sp
from flask import Blueprint, request, jsonify
from models import db, Task, Solution, Step
from flask_cors import cross_origin
from latex2sympy2 import latex2sympy  # Импортируем функцию для преобразования LaTeX в Sympy

solutions_bp = Blueprint('solutions', __name__, url_prefix='/api/solutions')

def safe_sympify(expr):
    """Безопасно преобразует LaTeX-выражение в формат sympy с обработкой ошибок,
    используя библиотеку latex2sympy2."""
    try:
        if expr.strip().upper() == "LIMIT":
            # Если получено значение LIMIT, возвращаем плейсхолдер (значение не вычисляем здесь)
            return sp.Integer(0)
        
        # Преобразуем LaTeX-выражение в sympy с помощью latex2sympy2
        sympy_expr = latex2sympy(expr)
        return sympy_expr
    except Exception as e:
        logging.error(f"Expression parsing error: '{expr}' - {str(e)}")
        raise ValueError(f"Cannot parse expression '{expr}': {str(e)}")

def check_algebraic_step(prev_expr_str, curr_expr_str, tolerance=1e-10):
    """Проверяет, корректно ли выполнено алгебраическое преобразование между двумя шагами."""
    try:
        # Пропускаем проверку для маркера LIMIT
        if prev_expr_str.strip().upper() == "LIMIT" or curr_expr_str.strip().upper() == "LIMIT":
            return {"is_correct": True, "error_type": None, "hint": None}

        # Преобразуем выражения через safe_sympify и упрощаем их
        prev_expr = sp.simplify(safe_sympify(prev_expr_str))
        curr_expr = sp.simplify(safe_sympify(curr_expr_str))
        
        # Если выражения эквивалентны, шаг корректен
        if prev_expr.equals(curr_expr):
            return {"is_correct": True, "error_type": None, "hint": None}
        
        # Если не эквивалентны – проверяем численно с подстановкой
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
                            "hint": f"Ваш шаг неверен. Для x={val}, предыдущее выражение = {prev_val:.6f}, текущее выражение = {curr_val:.6f}"
                        }
            except Exception:
                continue
                
        return {"is_correct": True, "error_type": None, "hint": None}
    except Exception as e:
        logging.error(f"Error checking step: {str(e)}")
        return {
            "is_correct": False, 
            "error_type": "parse_error", 
            "hint": f"Ошибка в выражении: {str(e)}"
        }

def check_limit(expr_str, var_str="x", limit_point="oo"):
    """Вычисляет предел выражения."""
    try:
        # Преобразуем выражение и определяем переменную
        expr = safe_sympify(expr_str)
        var = sp.Symbol(var_str)
        
        # Обрабатываем специальные точки предела
        if limit_point in ["infinity", "∞"]:
            limit_point = sp.oo
        elif limit_point in ["-infinity", "-∞"]:
            limit_point = -sp.oo
        else:
            limit_point = safe_sympify(limit_point)
        
        # Вычисляем предел
        limit_result = sp.limit(expr, var, limit_point)
        
        return {
            "is_correct": True,
            "computed_limit": limit_result,
            "error_type": None,
            "hint": None
        }
    except Exception as e:
        logging.error(f"Error computing limit: {str(e)}")
        return {
            "is_correct": False,
            "computed_limit": None,
            "error_type": "limit_error",
            "hint": f"Ошибка при вычислении предела: {str(e)}"
        }

@solutions_bp.route('/check', methods=['POST'])
@cross_origin()
def check_solution():
    """
    Проверяет полное решение, разбитое на шаги.
    Ожидаемый формат JSON:
    {
        "taskId": <task_id>,
        "steps": [
            "шаг 1", "шаг 2", ..., "LIMIT", "окончательный ответ"
        ]
    }
    """
    data = request.json
    logging.info(f"Received solution check request: {data}")
    
    # Валидация запроса
    if not data or "taskId" not in data or "steps" not in data:
        return jsonify({"error": "Invalid request format"}), 400
        
    task_id = data["taskId"]
    steps = data["steps"]
    
    if not isinstance(steps, list) or len(steps) < 2:
        return jsonify({
            "success": False,
            "errors": [{"step": 1, "error": "Решение должно состоять как минимум из двух шагов"}]
        }), 400
        
    # Получаем задачу из базы данных
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
        
    # Инициализация переменных
    errors = []
    algebraic_steps = []
    limit_index = -1
    found_limit = False
    
    # Поиск маркера LIMIT и сбор алгебраических шагов
    for i, step in enumerate(steps):
        if step.strip().upper() == "LIMIT":
            found_limit = True
            limit_index = i
            break
        algebraic_steps.append(step)
        
    # Если LIMIT не найден, а шагов не меньше двух, предполагаем, что последний шаг – предел
    if not found_limit and len(steps) >= 2:
        algebraic_steps = steps[:-1]
        steps.insert(len(steps)-1, "LIMIT")
        limit_index = len(steps) - 2
        found_limit = True
        
    if not algebraic_steps:
        return jsonify({
            "success": False,
            "errors": [{"step": 1, "error": "Алгебраические шаги отсутствуют", "hint": "Добавьте хотя бы один шаг перед LIMIT"}]
        }), 400
        
    # Проверка последовательных алгебраических шагов
    for i in range(len(algebraic_steps) - 1):
        prev_expr = algebraic_steps[i]
        curr_expr = algebraic_steps[i + 1]
        
        try:
            result = check_algebraic_step(prev_expr, curr_expr)
            if not result["is_correct"]:
                errors.append({
                    "step": i + 2,
                    "error": "Некорректное преобразование",
                    "hint": result["hint"] or "Проверьте алгебру"
                })
        except Exception as e:
            errors.append({
                "step": i + 2,
                "error": "Ошибка в выражении",
                "hint": f"Проверьте синтаксис: {str(e)}"
            })
            
    # Создаем запись решения
    user_id = 1  # Заглушка для идентификатора пользователя
    solution = Solution(task_id=task.id, user_id=user_id, status="in_progress")
    db.session.add(solution)
    db.session.flush()  # Получаем ID без коммита
    
    # Вычисляем предел, если ошибок не обнаружено
    computed_limit = None
    if found_limit and not errors:
        try:
            last_algebraic_expr = algebraic_steps[-1]
            
            # Определяем переменную и точку предела из данных задачи
            limit_var = "x"  # По умолчанию
            limit_point = "oo"  # По умолчанию (бесконечность)
            
            if task.limitVar:
                parts = task.limitVar.split("→")
                if len(parts) == 2:
                    limit_var = parts[0].strip()
                    limit_point = parts[1].strip()
            
            limit_result = check_limit(last_algebraic_expr, limit_var, limit_point)
            computed_limit = limit_result["computed_limit"]
            
            if not limit_result["is_correct"]:
                errors.append({
                    "step": limit_index + 1,
                    "error": "Ошибка при вычислении предела",
                    "hint": limit_result["hint"]
                })
                
            # Если после LIMIT указан окончательный ответ – сравниваем его с вычисленным пределом
            if limit_index < len(steps) - 1 and not errors:
                student_answer = steps[-1]
                try:
                    student_result = sp.simplify(safe_sympify(student_answer))
                    expected_result = sp.simplify(computed_limit)
                    
                    if not sp.simplify(student_result - expected_result).is_zero:
                        errors.append({
                            "step": len(steps),
                            "error": "Неверный окончательный ответ",
                            "hint": f"Ваш ответ не совпадает с вычисленным пределом: {computed_limit}"
                        })
                except Exception as e:
                    errors.append({
                        "step": len(steps),
                        "error": "Некорректный окончательный ответ",
                        "hint": f"Ошибка в окончательном ответе: {str(e)}"
                    })
        except Exception as e:
            logging.error(f"Limit calculation error: {str(e)}")
            errors.append({
                "step": limit_index + 1,
                "error": "Ошибка при обработке предела",
                "hint": f"Ошибка: {str(e)}"
            })
            
    # Сохранение шагов решения
    for i, step in enumerate(steps):
        is_correct = len(errors) == 0
        step_record = Step(
            solution_id=solution.id,
            step_number=i + 1,
            input_expr=step,
            is_correct=is_correct,
            error_type=None if is_correct else "error",
            hint=""
        )
        db.session.add(step_record)
        
    # Обновление статуса решения
    if errors:
        solution.status = "error"
    else:
        solution.status = "completed"
        
    db.session.commit()
    
    # Формирование ответа
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
