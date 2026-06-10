"""
run.py – Start Promoly backend.
On Windows, ProactorEventLoop must be set BEFORE uvicorn creates its loop.
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
import uvicorn

# Show all logs from our modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        loop="asyncio",
        log_level="info",
    )
