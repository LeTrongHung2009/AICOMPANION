"""
main_cli.py
===========
KIRA Desktop Companion - CLI Mode (Debug/Headless)
Runs without GUI for debugging or server deployment.
"""

import sys
import os
import asyncio
import logging

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from companion.utils.config import get_config
from companion.utils.logger import setup_logging
from companion.orchestrator import AsyncioOrchestrator

logger = logging.getLogger("kira.cli")

async def main():
    print("🚀 Starting KIRA Desktop Companion (CLI Mode)...")
    print("=" * 60)
    
    config = get_config()
    setup_logging(
        log_level="DEBUG" if config.debug_mode else "INFO",
        log_file=config.log_path
    )
    
    orchestrator = AsyncioOrchestrator(config)
    
    try:
        await orchestrator.start()
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await orchestrator.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
