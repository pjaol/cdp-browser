import pytest
import asyncio
import logging

logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
def event_loop():
    """Create an event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    
    # Clean up pending tasks
    pending = asyncio.all_tasks(loop)
    if pending:
        logger.debug(f"Cleaning up {len(pending)} pending tasks")
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close() 