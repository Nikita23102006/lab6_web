"""Лабораторная работа №6. Вариант 8. Все задания на одном сервере.

Запуск:  uvicorn main:app --reload
Открыть: http://127.0.0.1:8000/

FastAPI-приложения подключаются к общему приложению через mount().
Flask работает по другому стандарту (WSGI, синхронный), а FastAPI —
по ASGI (асинхронный). Переходник a2wsgi оборачивает Flask так,
что FastAPI может его подключить как обычное приложение.
"""

from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import adv01_flask_crud
import adv08_pydantic_schemas
import task04_table_page
import task08_fastapi_params
import task10_tasks_api

app = FastAPI(title="ЛР6 — вариант 8", docs_url=None, redoc_url=None)

SECTIONS = [
    ("/params", "Средн. №8", "FastAPI принимает параметр и отвечает",
     "FastAPI", task08_fastapi_params.app),
    ("/tasks-api", "Средн. №10", "Простейший REST API список задач",
     "FastAPI", task10_tasks_api.app),
    ("/table", "Средн. №4", "Страница с таблицей данных",
     "Flask", WSGIMiddleware(task04_table_page.app)),
    ("/schemas", "Повыш. №8", "Использование Pydantic-схем",
     "FastAPI", adv08_pydantic_schemas.app),
    ("/books", "Повыш. №1", "Flask с базой SQLite (CRUD)",
     "Flask", WSGIMiddleware(adv01_flask_crud.app)),
]

for prefix, _, _, _, sub_app in SECTIONS:
    app.mount(prefix, sub_app)


@app.get("/", response_class=HTMLResponse)
def index():
    rows = []
    for prefix, level, title, framework, _ in SECTIONS:
        if framework == "FastAPI":
            links = (f'<a href="{prefix}/docs">Swagger</a> · '
                     f'<a href="{prefix}/">JSON</a>')
        else:
            links = f'<a href="{prefix}/">открыть страницу</a>'
        rows.append(f"<tr><td>{level}</td><td>{title}</td>"
                    f"<td>{framework}</td><td>{links}</td></tr>")

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>ЛР6 — вариант 8</title>
<link rel="stylesheet" href="/table/static/style.css">
</head><body>
<header><h1>Лабораторная работа №6. Веб-программирование на Python</h1>
<p>Кострикин Н. А., группа 220042-11, вариант 8</p></header>
<main>
<table>
<thead><tr><th>Задание</th><th>Название</th><th>Фреймворк</th><th>Ссылки</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
<p class="muted">Все пять приложений работают на одном сервере uvicorn.</p>
</main></body></html>"""
