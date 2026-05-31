import unittest
import sys
from io import StringIO
import main  # Импортируем наш основной модуль main

# Класс для "плохого" источника, который не соответствует контракту
# Он нужен только для тестов, чтобы убедиться, что процессор его отфильтрует
class BrokenTestSource:
    def hello(self):
        return "I'm broken"


class TestTaskSystem(unittest.TestCase):

    def setUp(self):
        """
        запускается перед каждым тестовым методом
        Здесь мы инициализируем объекты, которые будут нужны во многих тестах
        """
        self.processor = lab1.TaskProcessor()
        self.file_source = lab1.FileSource("test_tasks.txt")
        self.api_source = lab1.ApiSource("http://test-api.com/tasks")
        self.generator_source = lab1.GeneratorSource(2) # Генерируем 2 задачи для теста
        self.broken_source = BrokenTestSource()


    def test_task_creation(self):
        """
        Проверяем, что объект Task создается корректно.
        """
        task = lab1.Task(id=1, payload="Test payload")
        self.assertEqual(task.id, 1)
        self.assertEqual(task.payload, "Test payload")
        self.assertIsInstance(task, lab1.Task) # Проверяем, что это экземпляр Task


    def test_file_source_get_tasks(self):

        #Проверяем, что FileSource возвращает список Task
        tasks = self.file_source.get_tasks()
        self.assertIsInstance(tasks, list) # Должен вернуть список
        self.assertGreater(len(tasks), 0) # Список не должен быть пустым
        self.assertIsInstance(tasks[0], lab1.Task) # Каждый элемент должен быть Task


    def test_api_source_get_tasks(self):

        #Проверяем, что ApiSource возвращает список Task
        tasks = self.api_source.get_tasks()
        self.assertIsInstance(tasks, list)
        self.assertGreater(len(tasks), 0)
        self.assertIsInstance(tasks[0], lab1.Task)


    def test_generator_source_get_tasks(self):

        #Проверяем, что GeneratorSource возвращает правильное количество Task
        tasks = self.generator_source.get_tasks()
        self.assertIsInstance(tasks, list)
        self.assertEqual(len(tasks), 2) # Мы задали генерацию 2 задач
        self.assertIsInstance(tasks[0], lab1.Task)


    def test_protocol_compliance(self):

        #Проверяем, что хорошие источники соответствуют протоколу, а плохой - нет
        self.assertTrue(isinstance(self.file_source, lab1.TaskSource))
        self.assertTrue(isinstance(self.api_source, lab1.TaskSource))
        self.assertTrue(isinstance(self.generator_source, lab1.TaskSource))
        self.assertFalse(isinstance(self.broken_source, lab1.TaskSource))


    def test_processor_valid_source(self):

        #Проверяем, что TaskProcessor успешно обрабатывает валидные источники
        #Мы будем перехватывать вывод в консоль, чтобы проверить сообщения
        # Перенаправляем stdout, чтобы захватить вывод консоли
        captured_output = StringIO()
        sys.stdout = captured_output

        # Загружаем задачи из валидного источника (например, FileSource)
        self.processor.load_from_source(self.file_source)

        # Восстанавливаем stdout
        sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        # Проверяем, что в выводе есть ожидаемые строки
        self.assertIn("[INFO] Источник валиден. Начинаем загрузку...", output)
        self.assertIn("Обработана задача ID:1", output) # Проверяем, что задачи обработаны
        self.assertIn("Обработана задача ID:2", output)


    def test_processor_invalid_source(self):

        #Проверяем, что TaskProcessor правильно отклоняет невалидные источники.
        # Перенаправляем stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        # Пытаемся загрузить задачи из невалидного источника
        self.processor.load_from_source(self.broken_source)

        # Восстанавливаем stdout
        sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        # Проверяем, что в выводе есть сообщение об ошибке
        self.assertIn("[ERROR] Ошибка! Переданный объект не является валидным источником задач.", output)
        self.assertIn("Объект типа BrokenTestSource не имеет метода get_tasks()", output)


# Запуск всех тестов, если этот файл запускается напрямую
if __name__ == '__main__':
    unittest.main()
