from typing import Protocol, List, Any, runtime_checkable
from dataclasses import dataclass


#1. Структура задачи
# Используем dataclass, так как это просто контейнер для данных.
@dataclass
class Task:
    id: int
    payload: Any


#2. Контракт (Protocol)
# Мы определяем контракт: "Любой класс, который имеет метод get_tasks,
# возвращающий список Task, считается источником задач".
# Декоратор @runtime_checkable нужен, чтобы работала проверка isinstance().
@runtime_checkable
class TaskSource(Protocol):
    def get_tasks(self) -> List[Task]:
        ...


#3. Источники задач (Реализация)
#эти классы НЕ наследуются от TaskSource.

class FileSource:
    """Источник, который 'читает' задачи из файла (имитация)."""

    def __init__(self, filename: str):
        self.filename = filename

    def get_tasks(self) -> List[Task]:
        print(f"-> Чтение задач из файла '{self.filename}'...")
        # Имитируем чтение строк
        data = ["Загрузить отчет", "Проверить почту"]
        return [Task(id=i + 1, payload=text) for i, text in enumerate(data)]


class ApiSource:
    """Источник, получающий задачи через API (заглушка)."""

    def __init__(self, url: str):
        self.url = url

    def get_tasks(self) -> List[Task]:
        print(f"-> Запрос к API по адресу {self.url}...")
        # Возвращаем другие данные
        return [
            Task(id=101, payload={"user": "admin", "cmd": "backup"}),
            Task(id=102, payload={"user": "guest", "cmd": "view"})
        ]


class GeneratorSource:
    """Источник, генерирующий задачи программно."""

    def __init__(self, count: int):
        self.count = count

    def get_tasks(self) -> List[Task]:
        print(f"-> Генерация {self.count} случайных задач...")
        tasks = []
        for i in range(self.count):
            tasks.append(Task(id=500 + i, payload=f"Auto-task #{i}"))
        return tasks


class BrokenSource:
    """Класс, который НЕ реализует контракт (нет метода get_tasks)."""

    def hello(self):
        print("Я просто класс, я не умею давать задачи.")


#4. Система приема задач

class TaskProcessor:
    def load_from_source(self, source: Any):
        """
        Метод принимает ЛЮБОЙ объект.
        Но внутри проверяет, соответствует ли он контракту TaskSource.
        """
        # ТЕХНИЧЕСКОЕ ТРЕБОВАНИЕ: проверка isinstance с протоколом
        if isinstance(source, TaskSource):
            print("\n[INFO] Источник валиден. Начинаем загрузку...")
            tasks = source.get_tasks()

            # Обработка задач
            for t in tasks:
                print(f"   Обработана задача ID:{t.id} | Данные: {t.payload}")
        else:
            print("\n[ERROR] Ошибка! Переданный объект не является валидным источником задач.")
            print(f"   Объект типа {type(source).__name__} не имеет метода get_tasks()")


#5. Запуск

if __name__ == "__main__":
    processor = TaskProcessor()

    # Создаем разные источники
    file_src = FileSource("tasks.txt")
    api_src = ApiSource("http://my-api.com/v1/tasks")
    gen_src = GeneratorSource(3)
    bad_src = BrokenSource()  # Это "неправильный" класс

    # Список всех наших потенциальных источников
    sources = [file_src, api_src, gen_src, bad_src]

    # Пытаемся обработать каждый
    for src in sources:
        processor.load_from_source(src)
