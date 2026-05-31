import asyncio, logging, time, uuid
from typing import Dict, Optional, Protocol
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

# Настройка
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Типы
class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskPriority(Enum):
    LOW = 0; NORMAL = 1; HIGH = 2; CRITICAL = 3

@dataclass
class TaskResult:
    success: bool
    data: any = None
    error: str = None
    exec_time: float = 0

@dataclass
class AsyncTask:
    type: str
    payload: dict
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    retries: int = 0
    result: Optional[TaskResult] = None

# Контракт обработчика
class TaskHandler(Protocol):
    @property
    def supported_type(self) -> str: ...
    async def execute(self, task: AsyncTask) -> TaskResult: ...

# Базовый класс для обработчиков
class BaseHandler:
    async def cleanup(self): pass

# ===== Примеры обработчиков =====
class ComputeHandler(BaseHandler):
    @property
    def supported_type(self) -> str: return "compute"
    
    async def execute(self, task: AsyncTask) -> TaskResult:
        op = task.payload.get("op")
        val = task.payload.get("val", 0)
        
        try:
            if op == "fib":
                result = await asyncio.to_thread(lambda: self._fib(val))
            elif op == "fact":
                result = await asyncio.to_thread(lambda: self._fact(val))
            else:
                return TaskResult(False, error="Unknown op")
            return TaskResult(True, data=result)
        except Exception as e:
            return TaskResult(False, error=str(e))
    
    def _fib(self, n): return n if n < 2 else self._fib(n-1) + self._fib(n-2)
    def _fact(self, n): return 1 if n < 2 else n * self._fact(n-1)

class SleepHandler(BaseHandler):
    @property
    def supported_type(self) -> str: return "sleep"
    
    async def execute(self, task: AsyncTask) -> TaskResult:
        delay = task.payload.get("delay", 1)
        await asyncio.sleep(delay)
        return TaskResult(True, data=f"Slept {delay}s")

# Контекстный менеджер
class ResourceManager:
    def __init__(self):
        self._handlers: Dict[str, BaseHandler] = {}
    
    def register(self, handler: BaseHandler):
        self._handlers[handler.supported_type] = handler
    
    def get(self, task_type: str) -> Optional[BaseHandler]:
        return self._handlers.get(task_type)
    
    @asynccontextmanager
    async def managed(self):
        try:
            yield self
        finally:
            for h in self._handlers.values():
                await h.cleanup()

# Асинхронная очередь
class AsyncQueue:
    def __init__(self):
        self._queues = {p: asyncio.Queue() for p in TaskPriority}
    
    async def put(self, task: AsyncTask):
        await self._queues[task.priority].put(task)
    
    async def get(self) -> Optional[AsyncTask]:
        for p in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
            if not self._queues[p].empty():
                return await self._queues[p].get()
        
        # Ждём любую задачу
        tasks = [self._queues[p].get() for p in TaskPriority]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for f in pending: f.cancel()
        return next(iter(done)).result()
    
    def task_done(self, task: AsyncTask):
        self._queues[task.priority].task_done()
    
    async def join(self):
        await asyncio.gather(*[q.join() for q in self._queues.values()])

# Асинхронный исполнитель
class AsyncExecutor:
    def __init__(self, workers: int = 3):
        self.workers_count = workers
        self.resources = ResourceManager()
        self.queue = AsyncQueue()
        self._running = False
        self._workers = []
        self.stats = {"total": 0, "ok": 0, "fail": 0}
    
    def register(self, handler: BaseHandler):
        self.resources.register(handler)
    
    async def submit(self, task_type: str, payload: dict, priority: TaskPriority = TaskPriority.NORMAL) -> str:
        task = AsyncTask(type=task_type, payload=payload, priority=priority)
        await self.queue.put(task)
        self.stats["total"] += 1
        logger.info(f"Submitted: {task.id} ({task_type})")
        return task.id
    
    async def _worker(self, wid: int):
        logger.info(f"Worker {wid} started")
        while self._running:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                if not task: continue
                
                handler = self.resources.get(task.type)
                if not handler:
                    task.result = TaskResult(False, error=f"No handler for {task.type}")
                    self.stats["fail"] += 1
                else:
                    task.status = TaskStatus.PROCESSING
                    start = time.time()
                    result = await handler.execute(task)
                    result.exec_time = time.time() - start
                    task.result = result
                    task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                    
                    if result.success:
                        self.stats["ok"] += 1
                        logger.info(f"Worker {wid} completed {task.id}")
                    else:
                        self.stats["fail"] += 1
                        logger.error(f"Worker {wid} failed {task.id}: {result.error}")
                
                self.queue.task_done(task)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {wid} error: {e}")
        logger.info(f"Worker {wid} stopped")
    
    async def start(self):
        if self._running: return
        self._running = True
        self._workers = [asyncio.create_task(self._worker(i)) for i in range(self.workers_count)]
        logger.info(f"Executor started with {self.workers_count} workers")
    
    async def stop(self):
        if not self._running: return
        logger.info("Stopping...")
        await self.queue.join()  # Ждём все задачи
        self._running = False
        for w in self._workers: w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("Stopped")
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, *args):
        await self.stop()


# Демонстрация
async def demo():
    # Создаём исполнитель
    async with AsyncExecutor(workers=3) as executor:
        # Регистрируем обработчики
        executor.register(ComputeHandler())
        executor.register(SleepHandler())
        
        # Отправляем задачи
        tasks = [
            executor.submit("compute", {"op": "fib", "val": 10}),
            executor.submit("compute", {"op": "fact", "val": 5}),
            executor.submit("sleep", {"delay": 0.5}),
            executor.submit("compute", {"op": "fib", "val": 15}),
            executor.submit("sleep", {"delay": 0.3}),
        ]
        
        await asyncio.gather(*tasks)
        await asyncio.sleep(2)  # Даём время на выполнение
    
    print(f"\nСтатистика: {executor.stats}")

if __name__ == "__main__":
    asyncio.run(demo())
