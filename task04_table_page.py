"""Задание средней сложности №4: страница с таблицей данных (Flask).

Запуск:  python3 task04_table_page.py
Открыть: http://127.0.0.1:5001/

Порт 5001, а не стандартный 5000: на macOS порт 5000 занят
службой AirPlay Receiver.
"""

from flask import Flask, render_template, request

app = Flask(__name__)

SUBJECTS = ("math", "physics", "programming")
SUBJECT_TITLES = {
    "math": "Математика",
    "physics": "Физика",
    "programming": "Программирование",
}

STUDENTS = [
    {"name": "Иванов И. И.", "group": "220042-11", "math": 4, "physics": 5, "programming": 5},
    {"name": "Петров П. П.", "group": "220042-11", "math": 3, "physics": 3, "programming": 4},
    {"name": "Сидорова А. В.", "group": "220042-12", "math": 5, "physics": 5, "programming": 5},
    {"name": "Кузнецов Д. А.", "group": "220042-11", "math": 2, "physics": 4, "programming": 3},
    {"name": "Смирнова Е. С.", "group": "220042-12", "math": 4, "physics": 4, "programming": 5},
    {"name": "Волков М. Ю.", "group": "220042-11", "math": 5, "physics": 4, "programming": 4},
    {"name": "Морозова О. Н.", "group": "220042-12", "math": 3, "physics": 2, "programming": 3},
    {"name": "Лебедев А. А.", "group": "220042-11", "math": 5, "physics": 5, "programming": 4},
]

SORTABLE = ("name", "group", *SUBJECTS, "average")


def with_average(student):
    """Возвращает копию записи с добавленным средним баллом."""
    marks = [student[subject] for subject in SUBJECTS]
    return {**student, "average": round(sum(marks) / len(marks), 2)}


def column_averages(rows):
    """Средние значения по каждому предмету — для строки итогов."""
    if not rows:
        return {}
    keys = (*SUBJECTS, "average")
    return {key: round(sum(row[key] for row in rows) / len(rows), 2)
            for key in keys}


@app.route("/")
def table():
    # Параметры из адресной строки: /?sort=average&order=desc&group=220042-11
    sort = request.args.get("sort", "name")
    order = request.args.get("order", "asc")
    group = request.args.get("group", "")

    # Не доверяем параметрам из адреса: неизвестное значение — значит, по умолчанию.
    if sort not in SORTABLE:
        sort = "name"
    if order not in ("asc", "desc"):
        order = "asc"

    rows = [with_average(student) for student in STUDENTS]
    groups = sorted({row["group"] for row in rows})

    if group in groups:
        rows = [row for row in rows if row["group"] == group]
    else:
        group = ""

    rows.sort(key=lambda row: row[sort], reverse=(order == "desc"))

    return render_template(
        "table.html",
        rows=rows,
        subjects=SUBJECTS,
        titles=SUBJECT_TITLES,
        totals=column_averages(rows),
        groups=groups,
        current_group=group,
        sort=sort,
        order=order,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
