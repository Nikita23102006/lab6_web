"""Задание повышенной сложности №1: Flask с базой SQLite (CRUD).

Запуск:  python3 adv01_flask_crud.py
Открыть: http://127.0.0.1:5002/

CRUD — четыре базовые операции с данными:
Create (создать), Read (прочитать), Update (изменить), Delete (удалить).
Предметная область — домашняя библиотека.
"""

import os
import sqlite3
from datetime import date

from flask import (
    Flask, abort, flash, g, redirect, render_template, request, url_for,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config.update(
    DATABASE=os.path.join(BASE_DIR, "library.db"),
    # Ключ нужен для flash-сообщений: они хранятся в подписанной cookie.
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-key-change-me"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT    NOT NULL,
    author  TEXT    NOT NULL,
    year    INTEGER NOT NULL,
    pages   INTEGER NOT NULL CHECK (pages > 0),
    is_read INTEGER NOT NULL DEFAULT 0
);
"""

SEED = [
    ("Мастер и Маргарита", "Михаил Булгаков", 1967, 480, 1),
    ("Преступление и наказание", "Фёдор Достоевский", 1866, 672, 1),
    ("Чистый код", "Роберт Мартин", 2008, 464, 0),
    ("Грокаем алгоритмы", "Адитья Бхаргава", 2016, 288, 0),
]


# ============================== База данных ==============================

def get_db():
    """Одно соединение на запрос. Хранится в g — объекте текущего запроса."""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row   # строки как словари: row["title"]
        # Встроенные LIKE и lower() в SQLite понимают регистр только
        # у латиницы: «Булгаков» не найдётся по запросу «булгаков».
        # Подключаем к SQLite питоновский str.lower — он знает кириллицу.
        g.db.create_function("py_lower", 1, py_lower, deterministic=True)
    return g.db


def py_lower(value):
    return value.lower() if isinstance(value, str) else value


@app.teardown_appcontext
def close_db(exception=None):
    """Вызывается Flask автоматически в конце каждого запроса."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Создаёт таблицу и заполняет примерами, если она пустая."""
    db = get_db()
    db.executescript(SCHEMA)
    count = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    if count == 0:
        db.executemany(
            "INSERT INTO books (title, author, year, pages, is_read) "
            "VALUES (?, ?, ?, ?, ?)", SEED)
    db.commit()


def get_book_or_404(book_id):
    book = get_db().execute(
        "SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        abort(404)
    return book


def validate(form):
    """Проверяет данные формы. Возвращает (данные, список ошибок)."""
    errors = []
    title = form.get("title", "").strip()
    author = form.get("author", "").strip()
    year_raw = form.get("year", "").strip()
    pages_raw = form.get("pages", "").strip()

    if not title:
        errors.append("Укажите название")
    if not author:
        errors.append("Укажите автора")

    try:
        year = int(year_raw)
        if not 1000 <= year <= date.today().year:
            errors.append(f"Год должен быть от 1000 до {date.today().year}")
    except ValueError:
        year = None
        errors.append("Год — целое число")

    try:
        pages = int(pages_raw)
        if pages <= 0:
            errors.append("Число страниц должно быть больше нуля")
    except ValueError:
        pages = None
        errors.append("Число страниц — целое число")

    data = {
        "title": title,
        "author": author,
        "year": year if year is not None else year_raw,
        "pages": pages if pages is not None else pages_raw,
        "is_read": 1 if form.get("is_read") else 0,
    }
    return data, errors


# ================================ Маршруты ================================

@app.route("/")
def index():
    """READ: список книг с поиском по названию и автору."""
    query = request.args.get("q", "").strip()

    if query:
        # Параметр подставляется через ?, а не через f-строку —
        # так SQL-инъекция невозможна.
        pattern = f"%{query.lower()}%"
        books = get_db().execute(
            "SELECT * FROM books "
            "WHERE py_lower(title) LIKE ? OR py_lower(author) LIKE ? "
            "ORDER BY title", (pattern, pattern)).fetchall()
    else:
        books = get_db().execute(
            "SELECT * FROM books ORDER BY title").fetchall()

    total_pages = sum(book["pages"] for book in books)
    read_count = sum(book["is_read"] for book in books)

    return render_template("books_list.html", books=books, query=query,
                           total_pages=total_pages, read_count=read_count)


@app.route("/new", methods=["GET", "POST"])
def create():
    """CREATE: GET показывает пустую форму, POST сохраняет."""
    if request.method == "POST":
        data, errors = validate(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            # Отдаём форму с тем, что пользователь уже ввёл.
            return render_template("book_form.html", book=data,
                                   action="Добавить"), 400

        db = get_db()
        db.execute(
            "INSERT INTO books (title, author, year, pages, is_read) "
            "VALUES (:title, :author, :year, :pages, :is_read)", data)
        db.commit()
        flash(f"Книга «{data['title']}» добавлена", "success")
        # Post/Redirect/Get: после POST — перенаправление, чтобы F5
        # не отправил форму повторно.
        return redirect(url_for("index"))

    empty = {"title": "", "author": "", "year": "", "pages": "", "is_read": 0}
    return render_template("book_form.html", book=empty, action="Добавить")


@app.route("/<int:book_id>/edit", methods=["GET", "POST"])
def edit(book_id):
    """UPDATE: форма заполнена текущими значениями."""
    book = get_book_or_404(book_id)

    if request.method == "POST":
        data, errors = validate(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            data["id"] = book_id
            return render_template("book_form.html", book=data,
                                   action="Сохранить"), 400

        db = get_db()
        db.execute(
            "UPDATE books SET title = :title, author = :author, year = :year, "
            "pages = :pages, is_read = :is_read WHERE id = :id",
            {**data, "id": book_id})
        db.commit()
        flash(f"Книга «{data['title']}» изменена", "success")
        return redirect(url_for("index"))

    return render_template("book_form.html", book=book, action="Сохранить")


@app.route("/<int:book_id>/delete", methods=["POST"])
def delete(book_id):
    """DELETE: только POST.

    Удаление по GET-ссылке опасно: браузер или поисковый робот
    может «перейти» по ней сам и стереть данные.
    """
    book = get_book_or_404(book_id)
    db = get_db()
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    flash(f"Книга «{book['title']}» удалена", "success")
    return redirect(url_for("index"))


@app.route("/<int:book_id>/toggle", methods=["POST"])
def toggle_read(book_id):
    """Быстрая смена отметки «прочитано» прямо из списка."""
    get_book_or_404(book_id)
    db = get_db()
    db.execute("UPDATE books SET is_read = 1 - is_read WHERE id = ?",
               (book_id,))
    db.commit()
    return redirect(url_for("index", q=request.args.get("q", "")))


# Таблица создаётся при импорте модуля — и при запуске напрямую,
# и при подключении через main.py.
with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True, port=5002)
