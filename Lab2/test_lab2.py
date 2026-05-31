import unittest
from lab2 import Task, ValidationError, InvalidPriorityError, InvalidStatusError


class TestTask(unittest.TestCase):

    def test_successful_creation(self):
        """Проверяем успешное создание задачи с валидными данными."""
        task = Task(id=1, description="Тестовое описание", priority=3, status="new")
        self.assertEqual(task.id, 1)
        self.assertEqual(task.description, "Тестовое описание")
        self.assertEqual(task.priority, 3)
        self.assertEqual(task.status, "new")

    def test_invalid_description_raises_error(self):
        """Проверяем, что пустое описание вызывает ошибку."""
        with self.assertRaises(ValidationError):
            Task(id=1, description="   ", priority=3, status="new")
        with self.assertRaises(ValidationError):
            Task(id=1, description="", priority=3, status="new")

    def test_invalid_priority_raises_error(self):
        """Проверяем, что некорректный приоритет вызывает ошибку."""
        with self.assertRaises(InvalidPriorityError):
            Task(id=1, description="Тест", priority=0, status="new")
        with self.assertRaises(InvalidPriorityError):
            Task(id=1, description="Тест", priority=6, status="new")
        with self.assertRaises(InvalidPriorityError):
            Task(id=1, description="Тест", priority="высокий", status="new")

    def test_invalid_status_raises_error(self):
        """Проверяем, что некорректный статус вызывает ошибку."""
        with self.assertRaises(InvalidStatusError):
            Task(id=1, description="Тест", priority=1, status="pending")

    def test_id_is_readonly(self):
        """Проверяем, что атрибут id доступен только для чтения."""
        task = Task(id=1, description="Тест", priority=1, status="new")
        with self.assertRaises(AttributeError):
            task.id = 99

    def test_computed_property_is_ready_to_start(self):
        """Проверяем работу вычисляемого свойства is_ready_to_start."""
        task = Task(id=1, description="Тест", priority=1, status="new")
        self.assertTrue(task.is_ready_to_start)

        task.status = "in_progress"
        self.assertFalse(task.is_ready_to_start)

        task.status = "done"
        self.assertFalse(task.is_ready_to_start)

    def test_creation_time_is_set(self):
        """Проверяем, что время создания устанавливается."""
        task = Task(id=1, description="Тест", priority=1, status="new")
        self.assertIsNotNone(task.created_at)


if __name__ == '__main__':
    unittest.main()
