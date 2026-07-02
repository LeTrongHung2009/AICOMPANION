"""
main_live2d.py
==============
KIRA Desktop Companion - Live2D Only Mode
Runs only the Live2D avatar overlay without chat widget.
Useful for streaming or minimal desktop presence.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("🚀 Starting KIRA Desktop Companion (Live2D Only Mode)...")
print("=" * 60)
print("⚠️  Note: Live2D overlay requires model files in assets/models/kira_live2d/")
print("   Download from: https://booth.pm/jp/items/4711410")
print("=" * 60)

try:
    from companion.desktop.live2d_overlay import Live2DOverlayApp
    
    if __name__ == "__main__":
        app = Live2DOverlayApp()
        exit_code = app.run()
        sys.exit(exit_code)
        
except ImportError as e:
    print(f"❌ Error importing Live2D module: {e}")
    print("\n💡 To fix this:")
    print("   1. Install PyQt6-WebEngine: pip install PyQt6-WebEngine")
    print("   2. Download Live2D model from Booth.pm")
    print("   3. Extract to: assets/models/kira_live2d/")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
