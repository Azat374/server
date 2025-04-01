import os
import logging
import io
from datetime import datetime
from flask import Blueprint, request, send_file, jsonify
from models import db, Solution, User, Task, Step
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

# Определяем базовую директорию
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
font_regular_path = os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf")
font_bold_path = os.path.join(BASE_DIR, "fonts", "DejaVuSans-Bold.ttf")
logging.info("Путь к DejaVuSans: %s", font_regular_path)
logging.info("Путь к DejaVuSans-Bold: %s", font_bold_path)

if not os.path.exists(font_regular_path) or not os.path.exists(font_bold_path):
    logging.error("Файл шрифта не найден. Проверьте пути к файлам шрифтов.")
else:
    pdfmetrics.registerFont(TTFont('DejaVuSans', font_regular_path))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_bold_path))

def wrap_text(text, max_width, c_obj, font, font_size):
    """
    Разбивает текст на строки так, чтобы ширина каждой строки не превышала max_width.
    """
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        if c_obj.stringWidth(test_line, font, font_size) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

@reports_bp.route('/pdf', methods=['POST'])
def generate_pdf_report():
    """
    Генерирует PDF-отчет с историей решений студентов, разбором ошибок и подсказками.
    Ожидается JSON с параметрами фильтрации: period (например, "2024-01-01:2024-02-01"),
    task_id и student_id (опционально).
    """
    try:
        data = request.json
        period = data.get("period")  # формат "YYYY-MM-DD:YYYY-MM-DD"
        task_id = data.get("task_id")
        student_id = data.get("student_id")

        query = Solution.query
        if period:
            try:
                start_str, end_str = period.split(":")
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_str, "%Y-%m-%d")
                # Расширяем конец периода до конца дня
                end_date = end_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Solution.created_at >= start_date, Solution.created_at <= end_date)
            except Exception as e:
                logging.error("Ошибка разбора периода: %s", e)
                return jsonify({"message": "Invalid period format. Use YYYY-MM-DD:YYYY-MM-DD"}), 400
        if task_id:
            query = query.filter(Solution.task_id == task_id)
        if student_id:
            query = query.filter(Solution.user_id == student_id)

        solutions = query.all()

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        margin = 50
        max_text_width = width - 2 * margin
        y = height - margin

        # Функция для отрисовки шапки на каждой странице
        def draw_header(c_obj):
            c_obj.setFont("DejaVuSans-Bold", 20)
            c_obj.drawCentredString(width / 2, height - margin + 20, "Отчет по решениям студентов")
            c_obj.line(margin, height - margin + 10, width - margin, height - margin + 10)

        draw_header(c)
        y -= 40
        c.setFont("DejaVuSans", 12)

        if not solutions:
            wrapped = wrap_text("Нет решений для заданного периода или фильтров.", max_text_width, c, "DejaVuSans", 12)
            for line in wrapped:
                c.drawString(margin, y, line)
                y -= 15
        else:
            for sol in solutions:
                if y < margin + 120:
                    c.showPage()
                    draw_header(c)
                    y = height - margin - 30

                # Формируем заголовок решения
                solution_header = (
                    f"Решение ID: {sol.id} | Пользователь: {sol.user.username} | "
                    f"Задача: {sol.task.title} | Статус: {sol.status} | Дата: {sol.created_at.strftime('%Y-%m-%d %H:%M')}"
                )
                header_lines = wrap_text(solution_header, max_text_width, c, "DejaVuSans-Bold", 12)
                c.setFont("DejaVuSans-Bold", 12)
                for line in header_lines:
                    c.drawString(margin, y, line)
                    y -= 15
                y -= 5

                c.setFont("DejaVuSans", 11)
                # Вывод шагов решения
                for step in sorted(sol.steps, key=lambda s: s.step_number):
                    step_text = f"Шаг {step.step_number}: {step.input_expr} — " + ("Корректно" if step.is_correct else "Некорректно")
                    if not step.is_correct:
                        step_text += f" (Ошибка: {step.error_type}; Подсказка: {step.hint})"
                    step_lines = wrap_text(step_text, max_text_width - 20, c, "DejaVuSans", 11)
                    for line in step_lines:
                        c.drawString(margin + 20, y, line)
                        y -= 12
                    if y < margin + 50:
                        c.showPage()
                        draw_header(c)
                        y = height - margin - 30

                y -= 10
                c.line(margin, y, width - margin, y)
                y -= 20

        c.showPage()
        c.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="report.pdf", mimetype="application/pdf")
    except Exception as e:
        logging.error("Ошибка генерации отчета: %s", e)
        return jsonify({"message": "Не удалось сгенерировать отчёт", "details": str(e)}), 500
