import random
import re
import logging
import sympy as sp
from flask import Blueprint, request, jsonify
from models import db, Task

tasks_generator_bp = Blueprint("tasks_generator", __name__, url_prefix="/api/tasks_generator")

# Пример шаблона задачи для категории "limits"
TEMPLATES = {
    "limits": [
        {
            "title": "lim (({par_a}x + {par_b})/({par_c}x + {par_d}))^(x+{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x + {par_b}}{{par_c}x + {par_d}} \right)^{x+{par_e}}",
            "expression": "(({par_a}*x + {par_b})/({par_c}*x + {par_d}))**(x+{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x + {par_b})/({par_c}x - {par_d}))^(x+{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x + {par_b}}{{par_c}x - {par_d}} \right)^{x+{par_e}}",
            "expression": "(({par_a}*x + {par_b})/({par_c}*x - {par_d}))**(x+{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x - {par_b})/({par_c}x + {par_d}))^(x+{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x - {par_b}}{{par_c}x + {par_d}} \right)^{x+{par_e}}",
            "expression": "(({par_a}*x - {par_b})/({par_c}*x + {par_d}))**(x+{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x - {par_b})/({par_c}x - {par_d}))^(x-{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x - {par_b}}{{par_c}x - {par_d}} \right)^{x-{par_e}}",
            "expression": "(({par_a}*x - {par_b})/({par_c}*x - {par_d}))**(x-{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x + {par_b})/({par_c}x + {par_d}))^(x*{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x + {par_b}}{{par_c}x + {par_d}} \right)^{x*{par_e}}",
            "expression": "(({par_a}*x + {par_b})/({par_c}*x + {par_d}))**(x*{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x + {par_b})/({par_c}x - {par_d}))^(x*{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x + {par_b}}{{par_c}x - {par_d}} \right)^{x*{par_e}}",
            "expression": "(({par_a}*x + {par_b})/({par_c}*x - {par_d}))**(x*{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x - {par_b})/({par_c}x + {par_d}))^(x*{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x - {par_b}}{{par_c}x + {par_d}} \right)^{x*{par_e}}",
            "expression": "(({par_a}*x - {par_b})/({par_c}*x + {par_d}))**(x*{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x - {par_b})/({par_c}x - {par_d}))^(x*{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x - {par_b}}{{par_c}x - {par_d}} \right)^{x*{par_e}}",
            "expression": "(({par_a}*x - {par_b})/({par_c}*x - {par_d}))**(x*{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x + {par_b})/({par_c}x + {par_d}))^(x-{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x + {par_b}}{{par_c}x + {par_d}} \right)^{x-{par_e}}",
            "expression": "(({par_a}*x + {par_b})/({par_c}*x + {par_d}))**(x-{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        # Дополнительные 10 вариантов со сложными операциями
        {
            "title": "lim (({par_a}x + {par_b})*({par_c}x + {par_d}))^(1/(x+{par_e}))",
            "description": r"\lim_{x\to\infty} \left( ({par_a}x + {par_b})({par_c}x + {par_d}) \right)^{\frac{1}{x+{par_e}}}",
            "expression": "(({par_a}*x + {par_b})*({par_c}*x + {par_d}))**(1/(x+{par_e}))",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (sqrt({par_a}x + {par_b})/({par_c}x + {par_d}))^(x+{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{\sqrt{{par_a}x + {par_b}}}{{par_c}x + {par_d}} \right)^{x+{par_e}}",
            "expression": "((({par_a}*x + {par_b})**0.5)/({par_c}*x + {par_d}))**(x+{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x + {par_b})/sqrt({par_c}x + {par_d}))^(x+{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x + {par_b}}{\sqrt{{par_c}x + {par_d}}} \right)^{x+{par_e}}",
            "expression": "(({par_a}*x + {par_b})/(({par_c}*x + {par_d})**0.5))**(x+{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x - {par_b})/({par_c}x + {par_d}))^(x**{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x - {par_b}}{{par_c}x + {par_d}} \right)^{x^{ {par_e} }}",
            "expression": "(({par_a}*x - {par_b})/({par_c}*x + {par_d}))**(x**{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x + {par_b})/({par_c}x - {par_d}))^(x**{par_e})",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x + {par_b}}{{par_c}x - {par_d}} \right)^{x^{ {par_e} }}",
            "expression": "(({par_a}*x + {par_b})/({par_c}*x - {par_d}))**(x**{par_e})",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x - {par_b})/({par_c}x + {par_d}))^(1/(x+{par_e}))",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x - {par_b}}{{par_c}x + {par_d}} \right)^{\frac{1}{x+{par_e}}}",
            "expression": "(({par_a}*x - {par_b})/({par_c}*x + {par_d}))**(1/(x+{par_e}))",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "lim (({par_a}x - {par_b})/({par_c}x - {par_d}))^(1/(x+{par_e}))",
            "description": r"\lim_{x\to\infty} \left( \frac{{par_a}x - {par_b}}{{par_c}x - {par_d}} \right)^{\frac{1}{x+{par_e}}}",
            "expression": "(({par_a}*x - {par_b})/({par_c}*x - {par_d}))**(1/(x+{par_e}))",
            "limitVar": "x→oo",
            "expected_value": "{expected_value}",
            "category": "limits",
            "params": {
                "par_a": (1, 5),
                "par_b": (1, 10),
                "par_c": (1, 5),
                "par_d": (1, 10),
                "par_e": (0, 3),
                "expected_value": "0"
            }
        }
    ],
    "integral_volterra_2": [
        {
            "title": "Вольтерра задача 1: {par_a}x - ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {
                "par_a": (1, 5),
                "par_b": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "Вольтерра задача 2: {par_a}x + ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {
                "par_a": (1, 5),
                "par_b": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "Вольтерра задача 3: {par_a}x - ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {
                "par_a": (1, 5),
                "par_b": (0, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "Вольтерра задача 4: {par_a}x + ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {
                "par_a": (1, 5),
                "par_b": (0, 3),
                "expected_value": "0"
            }
        },
        # Повторяем с незначительными вариациями для задач 5-20:
        {
            "title": "Вольтерра задача 5: {par_a}x - ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 6: {par_a}x + ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 7: {par_a}x - ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 8: {par_a}x + ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 9: {par_a}x - ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 10: {par_a}x + ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 11: {par_a}x - ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 12: {par_a}x + ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 13: {par_a}x - ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 14: {par_a}x + ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 15: {par_a}x - ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 16: {par_a}x + ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 17: {par_a}x - ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 18: {par_a}x + ∫₀ˣ (x-t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x-t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x-t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 19: {par_a}x - ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x - \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x - integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        },
        {
            "title": "Вольтерра задача 20: {par_a}x + ∫₀ˣ (x+t)φ(t) dt, φ(0)={par_b}",
            "description": r"\varphi(x) = {par_a}x + \int_{0}^{x} (x+t)\varphi(t) dt, \quad \varphi(0) = {par_b}",
            "expression": "{par_a}*x + integrate((x+t)*varphi(t), (t,0,x))",
            "limitVar": "0",
            "expected_value": "{expected_value}",
            "category": "integral_volterra_2",
            "params": {"par_a": (1, 5), "par_b": (0, 3), "expected_value": "0"}
        }
    ],
    "integral": [
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } {par_c}x^{ {par_d} } dx",
            "description": r"\int_{{par_a}}^{{par_b}} {par_c}x^{ {par_d} } dx",
            "expression": "integrate({par_c}*x**{par_d}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } ({par_c}x^{ {par_d} } + {par_e}) dx",
            "description": r"\int_{{par_a}}^{{par_b}} ({par_c}x^{ {par_d} } + {par_e}) dx",
            "expression": "integrate({par_c}*x**{par_d} + {par_e}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "par_e": (1, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } ({par_c}x^{ {par_d} } + {par_e}) dx",
            "description": r"\int_{{par_a}}^{{par_b}} ({par_c}x^{ {par_d} } + {par_e}) dx",
            "expression": "integrate({par_c}*x**{par_d} + {par_e}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "par_e": (1, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } ({par_c}x^{ {par_d} } + {par_e}) dx",
            "description": r"\int_{{par_a}}^{{par_b}} ({par_c}x^{ {par_d} } + {par_e}) dx",
            "expression": "integrate({par_c}*x**{par_d} + {par_e}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "par_e": (1, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } ({par_c}x^{ {par_d} } + {par_e}) dx",
            "description": r"\int_{{par_a}}^{{par_b}} ({par_c}x^{ {par_d} } + {par_e}) dx",
            "expression": "integrate({par_c}*x**{par_d} + {par_e}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "par_e": (1, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } ({par_c}x^{ {par_d} } + {par_e}) dx",
            "description": r"\int_{{par_a}}^{{par_b}} ({par_c}x^{ {par_d} } + {par_e}) dx",
            "expression": "integrate({par_c}*x**{par_d} + {par_e}, (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 3),
                "par_b": (4, 10),
                "par_c": (1, 5),
                "par_d": (1, 4),
                "par_e": (1, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } e^{{par_c}x} dx",
            "description": r"\int_{{par_a}}^{{par_b}} e^{{par_c}x} dx",
            "expression": "integrate(exp({par_c}*x), (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 2),
                "par_b": (3, 8),
                "par_c": (1, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } e^{{par_c}x} dx",
            "description": r"\int_{{par_a}}^{{par_b}} e^{{par_c}x} dx",
            "expression": "integrate(exp({par_c}*x), (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 2),
                "par_b": (3, 8),
                "par_c": (1, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } e^{{par_c}x} dx",
            "description": r"\int_{{par_a}}^{{par_b}} e^{{par_c}x} dx",
            "expression": "integrate(exp({par_c}*x), (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 2),
                "par_b": (3, 8),
                "par_c": (1, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } e^{{par_c}x} dx",
            "description": r"\int_{{par_a}}^{{par_b}} e^{{par_c}x} dx",
            "expression": "integrate(exp({par_c}*x), (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 2),
                "par_b": (3, 8),
                "par_c": (1, 3),
                "expected_value": "0"
            }
        },
        {
            "title": "∫_{ {par_a} }^{ {par_b} } e^{{par_c}x} dx",
            "description": r"\int_{{par_a}}^{{par_b}} e^{{par_c}x} dx",
            "expression": "integrate(exp({par_c}*x), (x, {par_a}, {par_b}))",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "integral",
            "params": {
                "par_a": (0, 2),
                "par_b": (3, 8),
                "par_c": (1, 3),
                "expected_value": "0"
            }
        }
    ],
    "algebra": [
        {
            "title": "Решите уравнение: {par_a}x^2 - {par_b}x + {par_c} = 0",
            "description": "{par_a}x^2 - {par_b}x + {par_c} = 0",
            "expression": "{par_a}*x**2 - {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: {par_a}x^2 + {par_b}x - {par_c} = 0",
            "description": "{par_a}x^2 + {par_b}x - {par_c} = 0",
            "expression": "{par_a}*x**2 + {par_b}*x - {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: -{par_a}x^2 + {par_b}x + {par_c} = 0",
            "description": "-{par_a}x^2 + {par_b}x + {par_c} = 0",
            "expression": "-{par_a}*x**2 + {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: -{par_a}x^2 - {par_b}x + {par_c} = 0",
            "description": "-{par_a}x^2 - {par_b}x + {par_c} = 0",
            "expression": "-{par_a}*x**2 - {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: {par_a}x^2 + {par_b}x + {par_c} = 0",
            "description": "{par_a}x^2 + {par_b}x + {par_c} = 0",
            "expression": "{par_a}*x**2 + {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: -{par_a}x^2 + {par_b}x - {par_c} = 0",
            "description": "-{par_a}x^2 + {par_b}x - {par_c} = 0",
            "expression": "-{par_a}*x**2 + {par_b}*x - {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: {par_a}x^2 - {par_b}x - {par_c} = 0",
            "description": "{par_a}x^2 - {par_b}x - {par_c} = 0",
            "expression": "{par_a}*x**2 - {par_b}*x - {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: -{par_a}x^2 - {par_b}x - {par_c} = 0",
            "description": "-{par_a}x^2 - {par_b}x - {par_c} = 0",
            "expression": "-{par_a}*x**2 - {par_b}*x - {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: {par_a}x^2 - {par_b}x + {par_c} = 0 (вариант 9)",
            "description": "{par_a}x^2 - {par_b}x + {par_c} = 0",
            "expression": "{par_a}*x**2 - {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: {par_a}x^2 + {par_b}x - {par_c} = 0 (вариант 10)",
            "description": "{par_a}x^2 + {par_b}x - {par_c} = 0",
            "expression": "{par_a}*x**2 + {par_b}*x - {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: -{par_a}x^2 + {par_b}x + {par_c} = 0 (вариант 11)",
            "description": "-{par_a}x^2 + {par_b}x + {par_c} = 0",
            "expression": "-{par_a}*x**2 + {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: -{par_a}x^2 - {par_b}x + {par_c} = 0 (вариант 12)",
            "description": "-{par_a}x^2 - {par_b}x + {par_c} = 0",
            "expression": "-{par_a}*x**2 - {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: {par_a}x^2 + {par_b}x + {par_c} = 0 (вариант 13)",
            "description": "{par_a}x^2 + {par_b}x + {par_c} = 0",
            "expression": "{par_a}*x**2 + {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: -{par_a}x^2 + {par_b}x - {par_c} = 0 (вариант 14)",
            "description": "-{par_a}x^2 + {par_b}x - {par_c} = 0",
            "expression": "-{par_a}*x**2 + {par_b}*x - {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: {par_a}x^2 - {par_b}x - {par_c} = 0 (вариант 15)",
            "description": "{par_a}x^2 - {par_b}x - {par_c} = 0",
            "expression": "{par_a}*x**2 - {par_b}*x - {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Решите уравнение: -{par_a}x^2 - {par_b}x - {par_c} = 0 (вариант 16)",
            "description": "-{par_a}x^2 - {par_b}x - {par_c} = 0",
            "expression": "-{par_a}*x**2 - {par_b}*x - {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Найдите корни уравнения: {par_a}x^2 - {par_b}x + {par_c} = 0 (вариант 17)",
            "description": "{par_a}x^2 - {par_b}x + {par_c} = 0",
            "expression": "{par_a}*x**2 - {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Найдите корни уравнения: {par_a}x^2 + {par_b}x - {par_c} = 0 (вариант 18)",
            "description": "{par_a}x^2 + {par_b}x - {par_c} = 0",
            "expression": "{par_a}*x**2 + {par_b}*x - {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Найдите корни уравнения: -{par_a}x^2 + {par_b}x + {par_c} = 0 (вариант 19)",
            "description": "-{par_a}x^2 + {par_b}x + {par_c} = 0",
            "expression": "-{par_a}*x**2 + {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        },
        {
            "title": "Найдите корни уравнения: {par_a}x^2 + {par_b}x + {par_c} = 0 (вариант 20)",
            "description": "{par_a}x^2 + {par_b}x + {par_c} = 0",
            "expression": "{par_a}*x**2 + {par_b}*x + {par_c}",
            "limitVar": "-",
            "expected_value": "{expected_value}",
            "category": "algebra",
            "params": {
            "par_a": (1, 5 ),
            "par_b": (1, 10),
            "par_c": (1, 10),
            "expected_value": "0"
            }
        }
    ]
}

def substitute_placeholders(text: str, substitutions: dict) -> str:
    """
    Заменяет все вхождения плейсхолдеров вида {par_...} в строке text на соответствующие значения из substitutions.
    
    Функция с помощью re.sub находит все шаблонные конструкции и заменяет их на строковое представление подстановки.
    """
    def repl(match):
        key = match.group(1)
        return str(substitutions.get(key, match.group(0)))
    return re.sub(r"\{(par_\w+)\}", repl, text)

def generate_random_task(template: dict) -> dict:
    """
    Создает задачу по шаблону:
      1. Из поля "params" генерирует подстановочные значения – для диапазонов (tuple) выбирается случайное число.
      2. Производится замена всех плейсхолдеров {par_...} в полях title, description, expression, limitVar и expected_value.
         Даже в description замена происходит внутри литеральных фигурных скобок для LaTeX.
      3. В зависимости от категории вычисляется expected_value:
         - Если категория "limits": вычисляется \(\lim_{x\to\infty} \text{expression}\).
         - Если категория "integral": вычисляется значение определённого интеграла.
         - Если категория "algebra": решается уравнение и возвращаются найденные корни.
         - Если категория "integral_volterra_2": вычисление не производится и expected_value остаётся заданным.
      4. Поле "params" удаляется из результата.
    """
    # Копируем шаблон, чтобы не изменять оригинал.
    task = dict(template)
    
    # Генерируем подстановки из params.
    substitutions = {}
    params = task.get("params", {})
    for key, value in params.items():
        if isinstance(value, tuple) and len(value) == 2:
            substitutions[key] = random.randint(value[0], value[1])
        else:
            substitutions[key] = value

    # Заменяем плейсхолдеры во всех требуемых строковых полях.
    for field in ["title", "description", "expression", "limitVar", "expected_value"]:
        if field in task and isinstance(task[field], str):
            task[field] = substitute_placeholders(task[field], substitutions)

    # Вычисляем expected_value в зависимости от категории.
    category = task.get("category")
    if category == "limits":
        try:
            x = sp.symbols('x')
            expr_str = task["expression"]
            expr = sp.sympify(expr_str)
            lim_val = sp.limit(expr, x, sp.oo)
            task["expected_value"] = str(lim_val)
        except Exception as e:
            logging.error(f"Ошибка вычисления expected_value для limits: {e}")
    elif category == "integral":
        try:
            x = sp.symbols('x')
            expr_str = task["expression"]
            expr = sp.sympify(expr_str)
            # Если выражение вычисляет определённый интеграл, то оно должно быть числовым.
            integral_val = expr.evalf()
            task["expected_value"] = str(integral_val)
        except Exception as e:
            logging.error(f"Ошибка вычисления expected_value для integral: {e}")
    elif category == "algebra":
        try:
            x = sp.symbols('x')
            expr_str = task["expression"]
            expr = sp.sympify(expr_str)
            # Решаем уравнение: ищем корни
            solutions = sp.solve(expr, x)
            task["expected_value"] = str(solutions)
        except Exception as e:
            logging.error(f"Ошибка вычисления expected_value для algebra: {e}")
    elif category == "integral_volterra_2":
        # Для этой категории вычисление не производится – оставляем expected_value таким, какое задано.
        pass

    # Удаляем служебное поле "params"
    if "params" in task:
        task.pop("params")
    return task

@tasks_generator_bp.route("", methods=["POST"])
def generate_tasks():
    """
    API-эндпоинт для генерации задач.
    
    Ожидает JSON вида:
      { "category": <категория>, "count": <количество задач> }
      
    Для выбранной категории случайным образом выбирается шаблон, подставляются случайные числа согласно диапазонам в "params",
    вычисляется expected_value через sympy и возвращается сформированный список задач.
    """
    try:
        data = request.get_json()
        category = data.get("category")
        count = int(data.get("count", 1))
        if category not in TEMPLATES:
            return jsonify({"error": "Неверная категория"}), 400
        templates = TEMPLATES[category]
        if not templates:
            return jsonify({"error": "Нет шаблонов для данной категории"}), 400

        generated_tasks = []
        for _ in range(count):
            random_template = random.choice(templates)
            task_generated = generate_random_task(random_template)
            generated_tasks.append(task_generated)
        return jsonify({"generated_tasks": generated_tasks}), 200
    except Exception as e:
        logging.error(f"Ошибка генерации задач: {e}")
        return jsonify({"error": str(e)}), 500

@tasks_generator_bp.route("/confirm", methods=["POST"])
def confirm_task():
    """
    API-эндпоинт для подтверждения (сохранения) задачи.
    
    Ожидает JSON с данными задачи, сохраняет её в базе и возвращает идентификатор сохранённой задачи.
    """
    try:
        task_data = request.get_json()
        new_task = Task(
            title=task_data.get("title"),
            description=task_data.get("description"),
            expression=task_data.get("expression"),
            limitVar=task_data.get("limitVar"),
            expected_value=task_data.get("expected_value"),
            category=task_data.get("category"),
        )
        db.session.add(new_task)
        db.session.commit()
        return jsonify({"message": "Задача успешно добавлена", "task_id": new_task.id}), 200
    except Exception as e:
        logging.error(f"Ошибка сохранения задачи: {e}")
        return jsonify({"error": str(e)}), 500

