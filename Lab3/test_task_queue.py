import unittest
import sys
from typing import List
from task_queue import (
    Task, TaskQueue, TaskStatus, TaskPriority, 
    TaskStreamProcessor, TaskQueueIterator
)


class TestTask(unittest.TestCase):
    """Тесты для класса Task"""
    
    def test_task_creation(self):
        task = Task(1, "Test Task", TaskPriority.HIGH, TaskStatus.PENDING)
        self.assertEqual(task.id, 1)
        self.assertEqual(task.name, "Test Task")
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertEqual(task.status, TaskStatus.PENDING)
    
    def test_task_equality(self):
        task1 = Task(1, "Task 1")
        task2 = Task(1, "Task 1")
        task3 = Task(2, "Task 2")
        
        self.assertEqual(task1, task2)
        self.assertNotEqual(task1, task3)


class TestTaskQueue(unittest.TestCase):
    """Тесты для класса TaskQueue"""
    
    def setUp(self):
        """Создание тестовой очереди"""
        self.queue = TaskQueue()
        self.task1 = Task(1, "Task 1", TaskPriority.LOW, TaskStatus.PENDING)
        self.task2 = Task(2, "Task 2", TaskPriority.HIGH, TaskStatus.IN_PROGRESS)
        self.task3 = Task(3, "Task 3", TaskPriority.CRITICAL, TaskStatus.COMPLETED)
        self.task4 = Task(4, "Task 4", TaskPriority.MEDIUM, TaskStatus.FAILED)
        
        self.queue.add_task(self.task1)
        self.queue.add_task(self.task2)
        self.queue.add_task(self.task3)
        self.queue.add_task(self.task4)
    
    def test_add_and_len(self):
        queue = TaskQueue()
        self.assertEqual(len(queue), 0)
        
        queue.add_task(Task(1, "Task 1"))
        self.assertEqual(len(queue), 1)
    
    def test_remove_task(self):
        removed = self.queue.remove_task(2)
        self.assertEqual(removed, self.task2)
        self.assertEqual(len(self.queue), 3)
        
        not_found = self.queue.remove_task(999)
        self.assertIsNone(not_found)
    
    def test_get_task(self):
        task = self.queue.get_task(3)
        self.assertEqual(task, self.task3)
        
        not_found = self.queue.get_task(999)
        self.assertIsNone(not_found)
    
    def test_update_task_status(self):
        result = self.queue.update_task_status(1, TaskStatus.IN_PROGRESS)
        self.assertTrue(result)
        self.assertEqual(self.queue.get_task(1).status, TaskStatus.IN_PROGRESS)
        
        result = self.queue.update_task_status(999, TaskStatus.COMPLETED)
        self.assertFalse(result)
    
    def test_iteration(self):
        tasks = list(self.queue)
        self.assertEqual(len(tasks), 4)
        self.assertEqual(tasks[0], self.task1)
        self.assertEqual(tasks[1], self.task2)
        self.assertEqual(tasks[2], self.task3)
        self.assertEqual(tasks[3], self.task4)
    
    def test_multiple_iterations(self):
        """Повторный обход очереди"""
        first_pass = list(self.queue)
        second_pass = list(self.queue)
        
        self.assertEqual(first_pass, second_pass)
        self.assertEqual(len(first_pass), 4)
    
    def test_modification_during_iteration(self):
        iterator = iter(self.queue)
        next(iterator)
        
        # Изменяем очередь во время итерации
        self.queue.add_task(Task(5, "Task 5"))
        
        with self.assertRaises(RuntimeError):
            next(iterator)
    
    def test_filter_by_status(self):
        pending_tasks = list(self.queue.filter_by_status(TaskStatus.PENDING))
        self.assertEqual(len(pending_tasks), 1)
        self.assertEqual(pending_tasks[0], self.task1)
        
        completed_tasks = list(self.queue.filter_by_status(TaskStatus.COMPLETED))
        self.assertEqual(len(completed_tasks), 1)
        self.assertEqual(completed_tasks[0], self.task3)
    
    def test_filter_by_priority(self):
        high_priority = list(self.queue.filter_by_priority(TaskPriority.HIGH))
        self.assertEqual(len(high_priority), 1)
        self.assertEqual(high_priority[0], self.task2)
        
        critical_priority = list(self.queue.filter_by_priority(TaskPriority.CRITICAL))
        self.assertEqual(len(critical_priority), 1)
        self.assertEqual(critical_priority[0], self.task3)
    
    def test_filter_by_priority_range(self):
        medium_to_high = list(self.queue.filter_by_priority_range(
            TaskPriority.MEDIUM, TaskPriority.HIGH
        ))
        self.assertEqual(len(medium_to_high), 2)
        self.assertIn(self.task2, medium_to_high)
        self.assertIn(self.task4, medium_to_high)
    
    def test_custom_filter(self):
        def is_completed_or_failed(task: Task) -> bool:
            return task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        
        filtered = list(self.queue.filter(is_completed_or_failed))
        self.assertEqual(len(filtered), 2)
        self.assertIn(self.task3, filtered)
        self.assertIn(self.task4, filtered)
    
    def test_map(self):
        names = list(self.queue.map(lambda t: t.name))
        self.assertEqual(names, ["Task 1", "Task 2", "Task 3", "Task 4"])
        
        ids = list(self.queue.map(lambda t: t.id))
        self.assertEqual(ids, [1, 2, 3, 4])
    
    def test_generator_lazy_evaluation(self):
        """Проверка ленивости генераторов"""
        filter_iter = self.queue.filter_by_status(TaskStatus.PENDING)
        self.assertTrue(hasattr(filter_iter, '__iter__'))
        self.assertTrue(hasattr(filter_iter, '__next__'))
        
        # Добавляем новую задачу после создания генератора
        new_task = Task(5, "New Task", TaskPriority.MEDIUM, TaskStatus.PENDING)
        self.queue.add_task(new_task)
        
        # Генератор должен видеть новые задачи
        pending_tasks = list(filter_iter)
        self.assertEqual(len(pending_tasks), 2)
    
    def test_clear(self):
        self.queue.clear()
        self.assertEqual(len(self.queue), 0)
        self.assertEqual(list(self.queue), [])
    
    def test_get_all_tasks_copy(self):
        tasks_copy = self.queue.get_all_tasks()
        self.assertEqual(len(tasks_copy), 4)
        
        tasks_copy.pop()
        self.assertEqual(len(self.queue), 4)


class TestTaskStreamProcessor(unittest.TestCase):
    """Тесты для потокового процессора задач"""
    
    def setUp(self):
        self.queue = TaskQueue()
        self.task1 = Task(1, "Task 1", TaskPriority.LOW, TaskStatus.COMPLETED)
        self.task2 = Task(2, "Task 2", TaskPriority.HIGH, TaskStatus.COMPLETED)
        self.task3 = Task(3, "Task 3", TaskPriority.CRITICAL, TaskStatus.PENDING)
        
        self.queue.add_task(self.task1)
        self.queue.add_task(self.task2)
        self.queue.add_task(self.task3)
    
    def test_filter_completed(self):
        completed = list(TaskStreamProcessor.filter_completed(iter(self.queue)))
        self.assertEqual(len(completed), 2)
        self.assertIn(self.task1, completed)
        self.assertIn(self.task2, completed)
    
    def test_group_by_priority(self):
        groups = TaskStreamProcessor.group_by_priority(iter(self.queue))
        
        self.assertEqual(len(groups[TaskPriority.LOW]), 1)
        self.assertEqual(len(groups[TaskPriority.HIGH]), 1)
        self.assertEqual(len(groups[TaskPriority.CRITICAL]), 1)
        self.assertEqual(len(groups[TaskPriority.MEDIUM]), 0)
    
    def test_batch_process(self):
        batches = list(TaskStreamProcessor.batch_process(iter(self.queue), 2))
        
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0]), 2)
        self.assertEqual(len(batches[1]), 1)


class TestPerformanceAndMemory(unittest.TestCase):
    """Тесты производительности и эффективности"""
    
    def test_large_queue_memory_efficiency(self):
        """Проверка, что фильтры не создают лишних копий"""
        queue = TaskQueue()
        
        for i in range(10000):
            priority = TaskPriority(i % 4)
            queue.add_task(Task(i, f"Task {i}", priority))
        
        import sys
        initial_size = sys.getsizeof(queue._tasks)
        
        filter_iter = queue.filter_by_priority(TaskPriority.HIGH)
        
        self.assertLess(sys.getsizeof(filter_iter), 1000)
        
        count = sum(1 for _ in filter_iter)
        self.assertEqual(count, 2500)
    
    def test_stop_iteration_handling(self):
        """Корректная обработка StopIteration"""
        queue = TaskQueue()
        queue.add_task(Task(1, "Task 1"))
        
        iterator = iter(queue)
        
        task = next(iterator)
        self.assertEqual(task.id, 1)
        
        with self.assertRaises(StopIteration):
            next(iterator)
    
    def test_empty_queue_iteration(self):
        """Итерация по пустой очереди"""
        queue = TaskQueue()
        
        count = sum(1 for _ in queue)
        self.assertEqual(count, 0)
        
        iterator = iter(queue)
        with self.assertRaises(StopIteration):
            next(iterator)


def run_tests():
    """Запуск всех тестов"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestTask))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskQueue))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskStreamProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceAndMemory))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Запуск тестов для очереди задач")
    print("=" * 60)
    
    test_result = run_tests()
    
    print("\n" + "=" * 60)
    if test_result.wasSuccessful():
        print("Все тесты пройдены успешно!")
    else:
        print(f"Пройдено {test_result.testsRun - len(test_result.failures) - len(test_result.errors)} из {test_result.testsRun} тестов")
    
    print("=" * 60)
