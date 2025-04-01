import sympy as sp

def safe_sympify(expr):
    """Безопасное преобразование выражения в sympy-формат."""
    try:
        if expr == "LIMIT":
            # Если приходит LIMIT, сразу возвращаем что-то
            # Но лучше вообще не передавать его как expr :)
            return sp.Integer(0)  # заглушка
        expr = expr.replace("e^{", "exp(").replace(r"\ln", "log")
        return sp.sympify(expr)
    except Exception as e:
        raise ValueError(f"Ошибка преобразования выражения '{expr}': {e}")

def check_algebraic_step(prev_expr_str, curr_expr_str, tolerance=1e-6):
    try:
        # Если в prev_expr_str = "LIMIT", можно пропустить проверку
        if prev_expr_str == "LIMIT":
            return {"is_correct": True, "error_type": None, "hint": "LIMIT как предыдущий шаг пропущен."}

        prev_expr = sp.simplify(safe_sympify(prev_expr_str))
        curr_expr = sp.simplify(safe_sympify(curr_expr_str))
        if prev_expr.equals(curr_expr):
            return {"is_correct": True, "error_type": None, "hint": ""}
        # Доп.числовая проверка
        for val in [1, 2, 3]:
            if abs(prev_expr.subs({'x': val}) - curr_expr.subs({'x': val})) > tolerance:
                return {
                    "is_correct": False,
                    "error_type": "algebraic_error",
                    "hint": "Ошибка в алгебраических преобразованиях. Проверьте сокращение или вынесение множителя."
                }
        return {"is_correct": True, "error_type": None, "hint": ""}
    except Exception as e:
        return {"is_correct": False, "error_type": "parse_error", "hint": f"Ошибка парсинга: {str(e)}"}

def check_limit(last_expr_str, expected_value_str):
    try:
        x = sp.Symbol('x')
        last_expr = safe_sympify(last_expr_str)
        computed_limit = sp.limit(last_expr, x, sp.oo)
        expected_value = safe_sympify(expected_value_str)
        if sp.simplify(computed_limit - expected_value) == 0:
            return {"is_correct": True, "computed_limit": computed_limit, "error_type": None, "hint": ""}
        else:
            return {
                "is_correct": False,
                "computed_limit": computed_limit,
                "error_type": "limit_error",
                "hint": f"Ожидаемый предел: {expected_value}"
            }
    except Exception as e:
        return {
            "is_correct": False,
            "error_type": "limit_parse_error",
            "hint": f"Ошибка вычисления предела: {str(e)}"
        }
