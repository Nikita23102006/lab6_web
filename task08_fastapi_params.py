"""Задание средней сложности №8: FastAPI принимает параметр и отвечает.

Запуск:  uvicorn task08_fastapi_params:app --reload
Документация Swagger:  http://127.0.0.1:8000/docs
"""

from datetime import date
from enum import Enum
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query

app = FastAPI(
    title="Задание 8 — параметры запроса",
    description="FastAPI принимает параметр и отвечает: "
                "параметры пути, параметры запроса, проверка значений.",
)

CURRENT_YEAR = date.today().year


class Language(str, Enum):
    """Допустимые языки. В Swagger превращаются в выпадающий список."""

    ru = "ru"
    en = "en"
    de = "de"


class Operation(str, Enum):
    add = "add"
    sub = "sub"
    mul = "mul"
    div = "div"


GREETINGS = {
    Language.ru: "Привет",
    Language.en: "Hello",
    Language.de: "Hallo",
}


@app.get("/")
def index():
    """Корень — подсказка, какие есть адреса."""
    return {
        "message": "Задание 8: FastAPI принимает параметр и отвечает",
        "examples": [
            "/hello/Никита",
            "/hello/Nikita?lang=en",
            "/square/12",
            "/calc?a=10&b=4&op=div",
            "/age?birth_year=2006",
        ],
        "docs": "/docs",
    }


@app.get("/hello/{name}")
def hello(
    name: Annotated[str, Path(min_length=1, max_length=50,
                              description="Имя для приветствия")],
    lang: Language = Language.ru,
):
    """Параметр пути name + необязательный параметр запроса lang."""
    return {
        "greeting": f"{GREETINGS[lang]}, {name}!",
        "name": name,
        "lang": lang,
        "length": len(name),
    }


@app.get("/square/{number}")
def square(number: int):
    """Параметр пути с типом int.

    FastAPI сам преобразует строку "12" из адреса в число 12,
    а на /square/abc вернёт ошибку 422 — до вызова функции дело не дойдёт.
    """
    return {"number": number, "square": number ** 2, "even": number % 2 == 0}


@app.get("/calc")
def calc(a: float, b: float, op: Operation = Operation.add):
    """Обязательные параметры запроса a и b, необязательный op."""
    if op == Operation.add:
        result = a + b
    elif op == Operation.sub:
        result = a - b
    elif op == Operation.mul:
        result = a * b
    else:
        if b == 0:
            # 422 — неверный формат данных, а здесь формат верный,
            # но значение недопустимо по смыслу. Для этого — 400.
            raise HTTPException(status_code=400, detail="Деление на ноль")
        result = a / b

    return {"a": a, "b": b, "operation": op, "result": result}


@app.get("/age")
def age(
    birth_year: Annotated[int, Query(ge=1900, le=CURRENT_YEAR,
                                     description="Год рождения")],
    name: Annotated[str | None, Query(max_length=50)] = None,
):
    """Числовой параметр с границами ge/le и необязательный name."""
    years = CURRENT_YEAR - birth_year
    who = name or "Вам"
    return {
        "birth_year": birth_year,
        "age": years,
        "message": f"{who}: в {CURRENT_YEAR} году исполняется {years}",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("task08_fastapi_params:app", host="127.0.0.1",
                port=8000, reload=True)
