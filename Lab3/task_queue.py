from enum import Enum
from typing import Any, Iterator, Optional, Callable, List, Dict


class TaskStatus(Enum):
    """Статусы задачи"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(Enum):
    """Приоритеты задачи"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class Task:
    """Класс, представляющий задачу"""
    
    def __init__(self, task_id: int, name: str, priority: TaskPriority = TaskPriority.MEDIUM,
                 status: TaskStatus = TaskStatus.PENDING):
        self.id = task_id
        self.name = name
        self.priority = priority
        self.status = status
    
    def __repr__(self) -> str:
        return f"Task(id={self.id}, name='{self.name}', priority={self.priority.name}, status={self.status.name})"
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Task):
            return False
        return self.id == other.id


class TaskQueueIterator:
    """Итератор для очереди задач с проверкой изменений"""
    
    def __init__(self, tasks: List[Task], version: int):
        self._tasks = tasks
        self._index = 0
        self._version = version
        self._original_version = version
    
    def __iter__(self) -> Iterator[Task]:
        return self
    
    def __next__(self) -> Task:
        if self._version != self._original_version:
            raise RuntimeError("Queue was modified during iteration")
        
        if self._index >= len(self._tasks):
            raise StopIteration
        
        task = self._tasks[self._index]
        self._index += 1
        return task


class TaskQueue:
    """Очередь задач с поддержкой итерации и ленивых фильтров"""
    
    def __init__(self):
        self._tasks: List[Task] = []
        self._version = 0
    
    def add_task(self, task: Task) -> None:
        """Добавление задачи в очередь"""
        self._tasks.append(task)
        self._version += 1
    
    def remove_task(self, task_id: int) -> Optional[Task]:
        """Удаление задачи по ID"""
        for i, task in enumerate(self._tasks):
            if task.id == task_id:
                removed = self._tasks.pop(i)
                self._version += 1
                return removed
        return None
    
    def get_task(self, task_id: int) -> Optional[Task]:
        """Получение задачи по ID"""
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None
    
    def update_task_status(self, task_id: int, status: TaskStatus) -> bool:
        """Обновление статуса задачи"""
        task = self.get_task(task_id)
        if task:
            task.status = status
            self._version += 1
            return True
        return False
    
    def __len__(self) -> int:
        return len(self._tasks)
    
    def __iter__(self) -> Iterator[Task]:
        return TaskQueueIterator(self._tasks, self._version)
    
    def _generate_filtered(self, predicate: Callable[[Task], bool]) -> Iterator[Task]:
        """Генератор для ленивой фильтрации задач"""
        for task in self._tasks:
            if predicate(task):
                yield task
    
    def filter_by_status(self, status: TaskStatus) -> Iterator[Task]:
        """Ленивая фильтрация задач по статусу"""
        return self._generate_filtered(lambda task: task.status == status)
    
    def filter_by_priority(self, priority: TaskPriority) -> Iterator[Task]:
        """Ленивая фильтрация задач по приоритету"""
        return self._generate_filtered(lambda task: task.priority == priority)
    
    def filter_by_priority_range(self, min_priority: TaskPriority, 
                                 max_priority: TaskPriority) -> Iterator[Task]:
        """Ленивая фильтрация задач по диапазону приоритетов"""
        return self._generate_filtered(
            lambda task: min_priority.value <= task.priority.value <= max_priority.value
        )
    
    def filter(self, predicate: Callable[[Task], bool]) -> Iterator[Task]:
        """Общая ленивая фильтрация задач по произвольному предикату"""
        return self._generate_filtered(predicate)
    
    def map(self, transform: Callable[[Task], Any]) -> Iterator[Any]:
        """Ленивое преобразование задач"""
        for task in self._tasks:
            yield transform(task)
    
    def get_all_tasks(self) -> List[Task]:
        """Получение всех задач (создаёт копию)"""
        return self._tasks.copy()
    
    def clear(self) -> None:
        """Очистка очереди задач"""
        self._tasks.clear()
        self._version += 1


class TaskStreamProcessor:
    """Класс для потоковой обработки задач с использованием генераторов"""
    
    @staticmethod
    def filter_completed(tasks: Iterator[Task]) -> Iterator[Task]:
        """Фильтрует завершённые задачи"""
        for task in tasks:
            if task.status == TaskStatus.COMPLETED:
                yield task
    
    @staticmethod
    def group_by_priority(tasks: Iterator[Task]) -> Dict[TaskPriority, List[Task]]:
        """Группирует задачи по приоритету"""
        groups = {priority: [] for priority in TaskPriority}
        for task in tasks:
            groups[task.priority].append(task)
        return groups
    
    @staticmethod
    def batch_process(tasks: Iterator[Task], batch_size: int) -> Iterator[List[Task]]:
        """Разбивает поток задач на батчи"""
        batch = []
        for task in tasks:
            batch.append(task)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch


# Точка входа для демонстрации
if __name__ == "__main__":
    # Демонстрация работы
    print("=" * 60)
    print("Демонстрация работы очереди задач")
    print("=" * 60)
    
    queue = TaskQueue()
    
    queue.add_task(Task(1, "Написать документацию", TaskPriority.HIGH, TaskStatus.PENDING))
    queue.add_task(Task(2, "Провести код-ревью", TaskPriority.CRITICAL, TaskStatus.PENDING))
    queue.add_task(Task(3, "Запустить тесты", TaskPriority.MEDIUM, TaskStatus.IN_PROGRESS))
    queue.add_task(Task(4, "Обновить зависимости", TaskPriority.LOW, TaskStatus.COMPLETED))
    
    print("\nВсе задачи:")
    for task in queue:
        print(f"  {task}")
    
    print("\nЗадачи с высоким приоритетом:")
    for task in queue.filter_by_priority_range(TaskPriority.HIGH, TaskPriority.CRITICAL):
        print(f"  {task.name} - {task.priority.name}")
