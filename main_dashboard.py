"""
main_dashboard.py
=================
KIRA Desktop Companion - Dashboard Entry Point
Launches the main application with dashboard UI for monitoring and control.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import PyQtAsyncApp

if __name__ == "__main__":
    print("🚀 Starting KIRA Desktop Companion (Dashboard Mode)...")
    print("=" * 60)
    app = PyQtAsyncApp()
    exit_code = app.run()
    sys.exit(exit_code)
