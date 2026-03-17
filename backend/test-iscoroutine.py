import asyncio

async def async_handler(data):
    print(f'Handler called with {data}')
    return 'result'

def sync_handler(data):
    print(f'Sync handler called with {data}')
    return 'result'

# Test async handler
result = async_handler({'test': 'data'})
print(f'Async handler returns: {type(result)}, iscoroutine={asyncio.iscoroutine(result)}')

# Test sync handler
result = sync_handler({'test': 'data'})
print(f'Sync handler returns: {type(result)}, iscoroutine={asyncio.iscoroutine(result)}')
