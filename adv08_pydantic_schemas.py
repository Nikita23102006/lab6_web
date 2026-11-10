"""Задание повышенной сложности №8: использование Pydantic-схем.

Запуск:  uvicorn adv08_pydantic_schemas:app --reload
Документация Swagger:  http://127.0.0.1:8000/docs

Две связанные сущности — пользователи и заказы. На них показано:
- ограничения полей через Field (длина, диапазон, шаблон);
- собственные проверки полей (field_validator) и модели целиком (model_validator);
- вложенные модели и списки моделей;
- вычисляемые поля (computed_field);
- разделение схем на входную, хранимую и выходную —
  чтобы пароль никогда не попал в ответ сервера;
- частичное обновление через exclude_unset.
"""

import hashlib
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, status
from pydantic import (
    BaseModel, ConfigDict, Field, computed_field, field_validator,
    model_validator,
)

app = FastAPI(
    title="Повышенное задание 8 — Pydantic-схемы",
    description="Пользователи и заказы: проверка входных данных, "
                "вложенные модели, вычисляемые поля, скрытие пароля.",
)

PROMO_CODES = {"STUDENT10": 10, "WELCOME5": 5}  # промокод -> скидка в %


# ============================== Пользователи ==============================

class Address(BaseModel):
    """Вложенная модель: используется внутри пользователя."""

    city: str = Field(min_length=2, max_length=50)
    street: str = Field(min_length=2, max_length=100)
    zip_code: str = Field(pattern=r"^\d{6}$", description="Шесть цифр")


class UserBase(BaseModel):
    """Общие поля для всех схем пользователя."""

    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,20}$",
                          description="Латиница, цифры, _; от 3 до 20 символов")
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
    full_name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=14, le=120)
    address: Address | None = None


class UserCreate(UserBase):
    """Входная схема регистрации: есть пароль и его подтверждение."""

    password: str = Field(min_length=8, max_length=64)
    password_confirm: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "username": "nikita_k",
            "email": "nikita@example.com",
            "full_name": "Кострикин Никита",
            "age": 19,
            "address": {"city": "Тула", "street": "пр. Ленина, 92",
                        "zip_code": "300012"},
            "password": "secret123",
            "password_confirm": "secret123",
        }
    })

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Убирает лишние пробелы: '  иван   петров ' -> 'Иван Петров'."""
        return " ".join(part.capitalize() for part in value.split())

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        """Пароль должен содержать и буквы, и цифры."""
        if not any(char.isdigit() for char in value):
            raise ValueError("пароль должен содержать хотя бы одну цифру")
        if not any(char.isalpha() for char in value):
            raise ValueError("пароль должен содержать хотя бы одну букву")
        return value

    @model_validator(mode="after")
    def passwords_match(self):
        """Проверка двух полей сразу — field_validator так не умеет."""
        if self.password != self.password_confirm:
            raise ValueError("пароли не совпадают")
        return self


class UserInDB(UserBase):
    """Схема хранения: вместо пароля — его хеш."""

    id: int
    password_hash: str
    created_at: datetime


class UserOut(UserBase):
    """Выходная схема: нет ни пароля, ни хеша.

    Даже если функция вернёт объект UserInDB, FastAPI пропустит его через
    response_model=UserOut, и лишние поля в ответ не попадут.
    """

    id: int
    created_at: datetime


class UserUpdate(BaseModel):
    """Схема частичного обновления: все поля необязательны."""

    email: str | None = Field(default=None,
                              pattern=r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    age: int | None = Field(default=None, ge=14, le=120)
    address: Address | None = None


# ================================ Заказы =================================

class OrderStatus(str, Enum):
    new = "new"
    paid = "paid"
    shipped = "shipped"
    cancelled = "cancelled"


class OrderItem(BaseModel):
    product: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=100)
    price: float = Field(gt=0, description="Цена за единицу, руб.")

    @computed_field
    @property
    def subtotal(self) -> float:
        """Сумма по позиции. Вычисляется, клиент её не присылает."""
        return round(self.quantity * self.price, 2)


class OrderCreate(BaseModel):
    user_id: int
    items: list[OrderItem] = Field(min_length=1, max_length=50)
    promo_code: str | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": 1,
            "items": [
                {"product": "Наушники", "quantity": 1, "price": 4990},
                {"product": "Кабель USB-C", "quantity": 2, "price": 490},
            ],
            "promo_code": "student10",
        }
    })

    @field_validator("promo_code")
    @classmethod
    def check_promo(cls, value: str | None) -> str | None:
        """Нормализует промокод и проверяет, что он существует."""
        if value is None:
            return None
        code = value.strip().upper()
        if code not in PROMO_CODES:
            raise ValueError(f"промокод {code} не существует")
        return code


class OrderOut(OrderCreate):
    id: int
    status: OrderStatus
    created_at: datetime

    @computed_field
    @property
    def total(self) -> float:
        return round(sum(item.subtotal for item in self.items), 2)

    @computed_field
    @property
    def discount_percent(self) -> int:
        return PROMO_CODES.get(self.promo_code, 0) if self.promo_code else 0

    @computed_field
    @property
    def total_with_discount(self) -> float:
        return round(self.total * (100 - self.discount_percent) / 100, 2)


# ============================ Хранилище в памяти ============================

users: dict[int, UserInDB] = {}
orders: dict[int, OrderOut] = {}


def hash_password(password: str) -> str:
    """Учебное хеширование. В настоящих проектах — bcrypt или argon2."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_user_or_404(user_id: int) -> UserInDB:
    if user_id not in users:
        raise HTTPException(status_code=404,
                            detail=f"Пользователь {user_id} не найден")
    return users[user_id]


# ================================ Маршруты ================================

@app.post("/users", response_model=UserOut,
          status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate):
    """Регистрация. Все проверки UserCreate выполнены ещё до вызова функции."""
    if any(user.username == data.username for user in users.values()):
        raise HTTPException(status_code=409,
                            detail=f"Имя {data.username} уже занято")

    user = UserInDB(
        id=len(users) + 1,
        password_hash=hash_password(data.password),
        created_at=datetime.now(),
        **data.model_dump(exclude={"password", "password_confirm"}),
    )
    users[user.id] = user
    return user          # UserInDB, но наружу уйдёт только то, что есть в UserOut


@app.get("/users", response_model=list[UserOut])
def list_users():
    return list(users.values())


@app.get("/users/{user_id}", response_model=UserOut)
def read_user(user_id: int):
    return get_user_or_404(user_id)


@app.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate):
    """Меняются только поля, которые клиент действительно прислал."""
    user = get_user_or_404(user_id)
    changes = data.model_dump(exclude_unset=True)
    # Старые значения + присланные изменения, и всё это снова через проверку.
    users[user_id] = UserInDB.model_validate({**user.model_dump(), **changes})
    return users[user_id]


@app.post("/orders", response_model=OrderOut,
          status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate):
    get_user_or_404(data.user_id)
    order = OrderOut(
        id=len(orders) + 1,
        status=OrderStatus.new,
        created_at=datetime.now(),
        **dict(data),    # поля модели как есть, без вычисляемых
    )
    orders[order.id] = order
    return order


@app.get("/orders/{order_id}", response_model=OrderOut)
def read_order(order_id: int):
    if order_id not in orders:
        raise HTTPException(status_code=404,
                            detail=f"Заказ {order_id} не найден")
    return orders[order_id]


@app.patch("/orders/{order_id}/status", response_model=OrderOut)
def change_status(order_id: int, new_status: OrderStatus):
    order = read_order(order_id)
    if order.status == OrderStatus.cancelled:
        raise HTTPException(status_code=400,
                            detail="Отменённый заказ изменить нельзя")
    order.status = new_status
    return order


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("adv08_pydantic_schemas:app", host="127.0.0.1",
                port=8000, reload=True)
