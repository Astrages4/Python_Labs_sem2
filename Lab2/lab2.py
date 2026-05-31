import time
from datetime import datetime
from typing import List, Any


#1. Пользовательские исключения для валидации
class ValidationError(ValueError):
    """Базовый класс для ошибок валидации."""
    pass


class InvalidPriorityError(ValidationError):
    """Вызывается, если приоритет не в допустимом диапазоне."""
    pass


class InvalidStatusError(ValidationError):
    """Вызывается, если статус не из списка разрешенных."""
    pass


# 2. Дескрипторы для валидации атрибутов

class ValidatedString:
    """
    Data Descriptor: проверяет, что строка не пустая.
    Data Descriptor, потому что реализует __set__.
    """

    def __set_name__(self, owner, name):
        # Сохраняем имя атрибута, к которому привязан дескриптор
        self.private_name = '_' + name

    def __get__(self, instance, owner):
        # Возвращаем значение из "приватного" поля объекта
        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        # Валидация при установке значения
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Описание не может быть пустым.")
        # Сохраняем значение в "приватное" поле
        setattr(instance, self.private_name, value)


class ValidatedPriority:
    """Data Descriptor: проверяет, что приоритет находится в диапазоне [1, 5]."""

    def __set_name__(self, owner, name):
        self.private_name = '_' + name

    def __get__(self, instance, owner):
        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        if not isinstance(value, int) or not (1 <= value <= 5):
            raise InvalidPriorityError("Приоритет должен быть целым числом от 1 до 5.")
        setattr(instance, self.private_name, value)


class ValidatedStatus:
    """Data Descriptor: проверяет, что статус один из разрешенных."""

    def __init__(self, *allowed_statuses):
        self.allowed = set(allowed_statuses)

    def __set_name__(self, owner, name):
        self.private_name = '_' + name

    def __get__(self, instance, owner):
        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        if value not in self.allowed:
            raise InvalidStatusError(f"Недопустимый статус. Разрешенные: {self.allowed}.")
        setattr(instance, self.private_name, value)


class CreationTime:
    """
    Non-Data Descriptor: устанавливает время создания только один раз.
    Non-Data, потому что реализует только __get__.
    """

    def __set_name__(self, owner, name):
        self.private_name = '_' + name

    def __get__(self, instance, owner):
        # Если у объекта еще нет этого атрибута, создаем его
        if not hasattr(instance, self.private_name):
            setattr(instance, self.private_name, datetime.now())
        return getattr(instance, self.private_name)


# 3. Обновленная модель задачи `Task`
# Теперь это не dataclass, а полноценный класс с логикой.
class Task:
    # Привязываем дескрипторы к атрибутам класса
    description = ValidatedString()
    priority = ValidatedPriority()
    # Указываем разрешенные статусы прямо при создании дескриптора
    status = ValidatedStatus("new", "in_progress", "done", "cancelled")
    created_at = CreationTime()

    def __init__(self, id: int, description: str, priority: int, status: str):
        # Атрибуты, управляемые дескрипторами
        self.description = description
        self.priority = priority
        self.status = status

        # Защищенный атрибут для id
        self._id = id

    @property
    def id(self) -> int:
        """
        Свойство (property) для 'id'.
        Оно делает атрибут доступным только для чтения.
        Попытка сделать task.id = 100 вызовет AttributeError.
        """
        return self._id

    @property
    def is_ready_to_start(self) -> bool:
        """
        Вычисляемое свойство. Его значение не хранится, а вычисляется
        на лету при каждом обращении.
        """
        return self.status == "new"

    def __repr__(self):
        """Метод для красивого отображения объекта."""
        return (f"Task(id={self.id}, description='{self.description}', "
                f"priority={self.priority}, status='{self.status}')")


# 4. Демонстрация работы
if __name__ == "__main__":
    print("--- Демонстрация работы Task ---")

    # 1. Успешное создание объекта
    try:
        task1 = Task(id=1, description="Сделать лабораторную №2", priority=5, status="new")
        print(f"Успешно создана задача: {task1}")
        print(f"ID (через property): {task1.id}")
        print(f"Готовность к запуску (вычисляемое свойство): {task1.is_ready_to_start}")
        print(f"Время создания (non-data descriptor): {task1.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    except ValidationError as e:
        print(f"Ошибка при создании: {e}")

    # 2. Попытка создать задачу с некорректным приоритетом
    print("\n--- Попытка создать задачу с приоритетом 10 ---")
    try:
        task2 = Task(id=2, description="Купить молоко", priority=10, status="new")
    except InvalidPriorityError as e:
        print(f"Ожидаемая ошибка: {e}")

    # 3. Попытка установить некорректный статус
    print("\n--- Попытка установить некорректный статус 'pending' ---")
    try:
        task1.status = "pending"
    except InvalidStatusError as e:
        print(f"Ожидаемая ошибка: {e}")

    # 4. Успешное изменение статуса и проверка вычисляемого свойства
    print("\n--- Изменение статуса на 'in_progress' ---")
    task1.status = "in_progress"
    print(f"Новый статус задачи: {task1.status}")
    print(f"Готовность к запуску после изменения статуса: {task1.is_ready_to_start}")

    # 5. Попытка изменить защищенный id
    print("\n--- Попытка изменить ID ---")
    try:
        task1.id = 100
    except AttributeError as e:
        print(f"Ожидаемая ошибка: {e}")

    # 6. Демонстрация разницы между data и non-data дескрипторами
    print("\n--- Демонстрация non-data descriptor ---")
    print(f"Время создания до прямого присваивания: {task1.created_at}")
    # Прямое присваивание атрибуту, управляемому non-data дескриптором,
    # переопределяет его в словаре экземпляра __dict__.
    task1.created_at = "Это теперь просто строка"
    print(f"Значение 'created_at' после прямого присваивания: {task1.created_at}")
    print(f"Словарь экземпляра: {task1.__dict__}")
    # А data-дескриптор не дал бы этого сделать, его __set__ всегда имеет приоритет.
