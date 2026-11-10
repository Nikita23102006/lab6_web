"""Задание средней сложности №10: простейший REST API «Список задач».

Запуск:  uvicorn task10_tasks_api:app --reload
Документация Swagger:  http://127.0.0.1:8000/docs

Данные хранятся в памяти процесса — после перезапуска сервера список
возвращается к начальному. Для учебного REST API этого достаточно.
"""

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI(
    title="Задание 10 — REST API списка задач",
    description="Создание, чтение, изменение и удаление задач.",
)


class TaskIn(BaseModel):
    """То, что присылает клиент: без id — его выдаёт сервер."""

    title: str
    description: str = ""
    done: bool = False


class Task(TaskIn):
    """То, что возвращает сервер: всё из TaskIn плюс id."""

    id: int


# «База данных» в памяти: словарь id -> задача.
tasks: dict[int, Task] = {}
next_id = 1


def add_task(data: TaskIn) -> Task:
    """Создаёт задачу с новым id."""
    global next_id
    task = Task(id=next_id, **data.model_dump())
    tasks[task.id] = task
    next_id += 1
    return task


def get_or_404(task_id: int) -> Task:
    """Возвращает задачу или прерывает обработку ответом 404."""
    if task_id not in tasks:
        raise HTTPException(status_code=404,
                            detail=f"Задача {task_id} не найдена")
    return tasks[task_id]


# Начальные данные, чтобы список не был пустым при первом запуске.
for title in ("Сделать ЛР6", "Запушить на GitHub", "Отправить ссылку боту"):
    add_task(TaskIn(title=title))


@app.get("/tasks", response_model=list[Task])
def list_tasks(done: bool | None = None):
    """GET /tasks — все задачи. ?done=true или ?done=false фильтруют."""
    result = list(tasks.values())
    if done is not None:
        result = [task for task in result if task.done == done]
    return result


@app.get("/tasks/{task_id}", response_model=Task)
def read_task(task_id: int):
    """GET /tasks/1 — одна задача."""
    return get_or_404(task_id)


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskIn):
    """POST /tasks — создать. Тело запроса — JSON по схеме TaskIn."""
    return add_task(data)


@app.put("/tasks/{task_id}", response_model=Task)
def replace_task(task_id: int, data: TaskIn):
    """PUT /tasks/1 — заменить задачу целиком."""
    get_or_404(task_id)
    task = Task(id=task_id, **data.model_dump())
    tasks[task_id] = task
    return task


@app.patch("/tasks/{task_id}/done", response_model=Task)
def mark_done(task_id: int, done: bool = True):
    """PATCH /tasks/1/done — отметить выполненной (или снять отметку)."""
    task = get_or_404(task_id)
    task.done = done
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    """DELETE /tasks/1 — удалить. Ответ 204: успешно, тела нет."""
    get_or_404(task_id)
    del tasks[task_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("task10_tasks_api:app", host="127.0.0.1",
                port=8000, reload=True)
