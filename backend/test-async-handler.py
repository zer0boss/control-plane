"""
Test: Verify async handler behavior
"""
import asyncio

async def async_handler(data):
    print(f'Async handler called with {data}')
    await asyncio.sleep(0.1)
    return 'result'

def sync_handler(data):
    print(f'Sync handler called with {data}')
    return 'result'

async def main():
    test_data = {'test': 'data'}

    # Test async handler - calling without await
    print("=== Test 1: Calling async handler without await ===")
    result = async_handler(test_data)
    print(f'Result type: {type(result)}, iscoroutine: {asyncio.iscoroutine(result)}')

    # Create task (current code behavior)
    print("Creating task...")
    task = asyncio.create_task(result)
    print(f'Task created: {task}')
    await asyncio.sleep(0.2)  # Wait for task to complete
    print(f'Task done: {task.done()}, result: {task.result()}')

    # Test async handler - calling with await
    print("\n=== Test 2: Calling async handler with await ===")
    result2 = await async_handler(test_data)
    print(f'Result: {result2}')

    # Test sync handler
    print("\n=== Test 3: Calling sync handler ===")
    result3 = sync_handler(test_data)
    print(f'Result type: {type(result3)}, iscoroutine: {asyncio.iscoroutine(result3)}')

if __name__ == "__main__":
    asyncio.run(main())
