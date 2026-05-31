import asyncio, pytest
from async_executor import *

@pytest.mark.asyncio
async def test_basic_execution():
    executor = AsyncExecutor(workers=2)
    executor.register(ComputeHandler())
    
    await executor.start()
    task_id = await executor.submit("compute", {"op": "fib", "val": 5})
    await asyncio.sleep(0.5)
    await executor.stop()
    
    assert executor.stats["total"] == 1
    assert executor.stats["ok"] == 1

@pytest.mark.asyncio
async def test_multiple_tasks():
    executor = AsyncExecutor(workers=3)
    executor.register(ComputeHandler())
    executor.register(SleepHandler())
    
    await executor.start()
    
    ids = await asyncio.gather(
        executor.submit("compute", {"op": "fib", "val": 10}),
        executor.submit("sleep", {"delay": 0.2}),
        executor.submit("compute", {"op": "fact", "val": 6}),
    )
    
    await asyncio.sleep(2)
    await executor.stop()
    
    assert executor.stats["total"] == 3
    assert executor.stats["ok"] == 3

@pytest.mark.asyncio
async def test_unknown_handler():
    executor = AsyncExecutor(workers=1)
    await executor.start()
    
    await executor.submit("unknown", {})
    await asyncio.sleep(0.5)
    await executor.stop()
    
    assert executor.stats["fail"] == 1

@pytest.mark.asyncio
async def test_context_manager():
    async with AsyncExecutor(workers=2) as executor:
        executor.register(ComputeHandler())
        await executor.submit("compute", {"op": "fib", "val": 8})
        await asyncio.sleep(0.5)
    
    assert executor.stats["ok"] == 1

@pytest.mark.asyncio
async def test_priority():
    executor = AsyncExecutor(workers=1)
    executor.register(SleepHandler())
    
    await executor.start()
    
    await executor.submit("sleep", {"delay": 0.1}, TaskPriority.LOW)
    await executor.submit("sleep", {"delay": 0.1}, TaskPriority.CRITICAL)
    
    await asyncio.sleep(1)
    await executor.stop()
    
    assert executor.stats["total"] == 2

if __name__ == "__main__":
    asyncio.run(demo())
    pytest.main([__file__, "-v"])
