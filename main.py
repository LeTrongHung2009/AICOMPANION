"""
main.py
=======
MyCompanion AI Entrypoint.
Orchestrates PyQt6 app loop and maps the AsyncioOrchestrator into a shared thread.
"""

from __future__ import annotations

import sys
import logging
import asyncio
from pathlib import Path

from PyQt6.QtWidgets import QApplication
import qasync  # <-- Cần thiết cho PyQt + Asyncio

# Import components
from companion.utils.config import get_config
from companion.utils.logger import setup_logging
from companion.model_setup.attribution import show_attribution
from companion.orchestrator import AsyncioOrchestrator

logger = logging.getLogger("mycompanion.main")

class PyQtAsyncApp:
    """
    Integrates PyQt6 application thread loop with asyncio task runners using qasync.
    Ensures safe, responsive single-loop non-blocking desktop behavior.
    """

    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.config = get_config()
        
        # 1. SETUP EVENT LOOP FIRST (Rất quan trọng!)
        # Phải thiết lập loop trước khi bất kỳ class asyncio nào được khởi tạo
        self.loop = qasync.QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        # Setup logging configurations
        setup_logging(
            log_level="DEBUG" if self.config.debug_mode else "INFO",
            log_file=self.config.log_path
        )

        # Print model attribution
        show_attribution()

        # 2. KHỞI TẠO ORCHESTRATOR SAU KHI LOOP ĐÃ SẴN SÀNG
        self.orchestrator = AsyncioOrchestrator(self.config)

    def run(self) -> int:
        with self.loop:
            # Start async tasks inside the blended context
            self.loop.create_task(self.orchestrator.start())
            
            # Start the integrated Qt/Asyncio loop
            try:
                exit_code = self.loop.run_forever()
            except KeyboardInterrupt:
                logger.info("Application interrupted by user.")
                exit_code = 0
            finally:
                # Shutdown async engines cleanly
                self.loop.run_until_complete(self.orchestrator.stop())
                
        return exit_code

if __name__ == "__main__":
    # Ensure sys.argv carries proper platform paths
    sys.exit(PyQtAsyncApp().run())
