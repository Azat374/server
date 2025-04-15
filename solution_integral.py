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

def evaluate_integrals(expr):
    """
    Рекурсивно ищет в выражении все объекты Integral и вычисляет их,
    подставляя вычисленные значения вместо неопределённых интегралов.
    """
    integrals = list(expr.atoms(sp.Integral))
    for integral in integrals:
        try:
            evaluated = sp.integrate(integral.function, *integral.limits)
            expr = expr.subs(integral, evaluated)
        except Exception as e:
            logging.error(f"Ошибка при вычислении интеграла {integral}: {e}")
    return expr

def check_algebraic_step(prev_expr_str, curr_expr_str, tolerance=1e-10):
    """
    Проверяет корректность алгебраического преобразования между двумя шагами.
    Если один из шагов равен "LIMIT", проверка пропускается.
    
    1. Преобразует строки LaTeX в sympy-выражения.
    2. Вычисляет интегралы внутри выражений (через evaluate_integrals) и упрощает результат.
    3. Сначала выполняется символическая проверка (equals), а при необходимости – численная,
       подставляя тестовые значения переменной \( x \).
    """
    try:
        if prev_expr_str.strip().upper() == "LIMIT" or curr_expr_str.strip().upper() == "LIMIT":
            return {"is_correct": True, "error_type": None, "hint": None}
        
        # Преобразование в символьное представление и вычисление интегралов
        prev_expr_raw = safe_sympify(prev_expr_str)
        curr_expr_raw = safe_sympify(curr_expr_str)
        prev_expr = sp.simplify(evaluate_integrals(prev_expr_raw))
        curr_expr = sp.simplify(evaluate_integrals(curr_expr_raw))
        
        # Символическая проверка
        if prev_expr.equals(curr_expr):
            return {"is_correct": True, "error_type": None, "hint": None}
        
        # Если символическое сравнение не дало результата, выполняется численная проверка
        x = sp.Symbol('x')
        test_values = [1, 2, 3, 5, 10, 100]
        for val in test_values:
            try:
                prev_val = float(prev_expr.subs({x: val}))
                curr_val = float(curr_expr.subs({x: val}))
                if abs(prev_val - curr_val) > tolerance:
                    return {
                        "is_correct": False,
                        "error_type": "algebraic_error",
                        "hint": f"При x={val}: предыдущее значение = {prev_val:.6f}, текущее значение = {curr_val:.6f}"
                    }
            except Exception:
                continue
        return {"is_correct": True, "error_type": None, "hint": None}
    except Exception as e:
        logging.error(f"Error checking step: {str(e)}")
        return {"is_correct": False, "error_type": "parse_error", "hint": f"Ошибка: {str(e)}"}

def check_integral_solution_final(final_solution_str, var_str="x"):
    """
    Проверяет окончательный ответ по интегральной задаче Вольтерры второго рода:
        φ(x) = x - ∫₀ˣ (x-t) φ(t) dt.
    
    Для данного примера верное решение должно удовлетворять следующему:
    
        1. Начальное условие: φ(0) = 0.
        2. Производная в точке 0: φ'(0) = 1.
        3. Дифференциальное уравнение: φ''(x) + φ(x) = 0.
    
    Если все условия выполнены, решение считается корректным (как для sin x).
    """
    try:
        x = sp.Symbol(var_str)
        F_expr = sp.simplify(safe_sympify(final_solution_str))
        # Проверка начального условия: φ(0)=0
        if not sp.Eq(F_expr.subs(x, 0), 0):
            return {"is_correct": False, "error_type": "integral_error", 
                    "hint": f"Начальное условие неверно: φ(0) должно быть 0, получено {F_expr.subs(x, 0)}"}
        # Проверка производной в нуле: φ'(0)=1
        F_prime = sp.diff(F_expr, x)
        if not sp.Eq(F_prime.subs(x, 0), 1):
            return {"is_correct": False, "error_type": "integral_error", 
                    "hint": f"Производная в точке 0 неверна: φ'(0) должно быть 1, получено {F_prime.subs(x, 0)}"}
        # Проверка дифференциального уравнения: φ''(x)+φ(x)=0
        F_double = sp.diff(F_expr, x, 2)
        residual = sp.simplify(F_double + F_expr)
        if not residual.equals(0):
            # Проверим остаток для нескольких значений x
            test_values = [0.5, 1, 2]
            for val in test_values:
                res_val = residual.subs(x, val)
                if abs(float(res_val)) > 1e-6:
                    return {"is_correct": False, "error_type": "integral_error", 
                            "hint": f"Функция не удовлетворяет дифференциальному уравнению: φ''(x) + φ(x) ≠ 0 при x={val}, получено {res_val}"}
        return {"is_correct": True, "error_type": None, "hint": None}
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
         { "label": "\\varphi_0(x)", "steps": ["шаг 1", "шаг 2", ...] },
         { ... }  // возможно, несколько φ-функций
      ],
      "finalSolution": "LaTeX строки с окончательным ответом"
    }
    
    Для интегральных задач Вольтерры второго рода уравнение имеет вид:
         φ(x) = x - ∫₀ˣ (x-t) φ(t) dt.
    """
    data = request.json
    logging.info(f"Received integral solution check request: {data}")
    
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

    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    errors = []  # Список ошибок для φ-функций и окончательного ответа

    # Проверка последовательности шагов для каждой φ-функции
    for phi_index, phi in enumerate(phi_steps):
        if "steps" not in phi or not isinstance(phi["steps"], list):
            errors.append({
                "phiIndex": phi_index,
                "error": "Отсутствуют шаги для φ-функции",
                "hint": "Добавьте хотя бы один шаг для этой φ-функции"
            })
            continue

        steps = phi["steps"]
        if len(steps) < 1:
            errors.append({
                "phiIndex": phi_index,
                "error": "Функция должна содержать хотя бы один шаг",
                "hint": "Заполните шаги для данной φ-функции"
            })
            continue

        if len(steps) == 1:
            continue

        for i in range(len(steps) - 1):
            result = check_algebraic_step(steps[i], steps[i + 1])
            if not result["is_correct"]:
                errors.append({
                    "phiIndex": phi_index,
                    "stepIndex": i + 1,
                    "error": "Некорректное преобразование",
                    "hint": result["hint"] or "Проверьте шаги"
                })

    # Проверка окончательного ответа по интегральной задаче
    if not final_solution.strip():
        errors.append({
            "phiIndex": -1,
            "error": "Окончательный ответ отсутствует",
            "hint": "Введите окончательный ответ по интегралу"
        })
    else:
        integral_check = check_integral_solution_final(final_solution, var_str="x")
        if not integral_check["is_correct"]:
            errors.append({
                "phiIndex": -1,
                "error": "Неверный окончательный ответ",
                "hint": integral_check["hint"]
            })

    user_id = 1  # Заглушка для идентификатора пользователя
    solution = Solution(task_id=task.id, user_id=user_id, status="in_progress")
    db.session.add(solution)
    db.session.flush()  # Для получения solution.id без коммита

    step_counter = 1
    for phi_index, phi in enumerate(phi_steps):
        steps = phi.get("steps", [])
        for step_index, step in enumerate(steps):
            is_error = False
            error_hint = ""
            for error in errors:
                if error.get("phiIndex") == phi_index and error.get("stepIndex") == step_index:
                    is_error = True
                    error_hint = error.get("hint", "")
                    break
            step_record = Step(
                solution_id=solution.id,
                step_number=step_counter,
                input_expr=phi_index*1000+step,
                is_correct=not is_error,
                error_type="error" if is_error else None,
                hint=error_hint
            )
            db.session.add(step_record)
            step_counter += 1

    final_error = next((error for error in errors if error.get("phiIndex") == -1), None)
    final_step_record = Step(
        solution_id=solution.id,
        step_number=step_counter,
        input_expr=final_solution,
        is_correct=not final_error,
        error_type="error" if final_error else None,
        hint=final_error.get("hint", "") if final_error else ""
    )
    db.session.add(final_step_record)

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




@solution_integral_bp.route('/last-integral/<int:task_id>', methods=['GET'])
def get_last_integral_solution(task_id):
    solution = Solution.query.filter_by(task_id=task_id).order_by(Solution.created_at.desc()).first()
    if not solution:
        return jsonify({"phiSteps": [], "final": ""})

    steps = Step.query.filter_by(solution_id=solution.id).order_by(Step.step_number).all()

    phi_dict = {}
    final = ""

    for step in steps:
        try:
            if step == steps[-1]:
                final = step.input_expr
                continue

            # Парсим phi_index и шаг
            val = step.input_expr
            if isinstance(val, str) and val.isdigit():
                val = int(val)

            phi_index = val // 1000
            step_latex = val % 1000

            label = f"\\varphi_{phi_index}(x)"
            if label not in phi_dict:
                phi_dict[label] = []
            phi_dict[label].append(str(step_latex))
        except Exception as e:
            logging.warning(f"Ошибка парсинга шага: {e}")

    phiSteps = [{"label": label, "steps": steps} for label, steps in phi_dict.items()]

    return jsonify({"phiSteps": phiSteps, "final": final})
