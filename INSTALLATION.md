# 📦 KIRA Installation Guide

## ✅ Fixed Issues

### 1. **Missing Entry Point Files**
Created three entry points for different use cases:
- `main_dashboard.py` - Full GUI with dashboard (recommended)
- `main_cli.py` - Headless CLI mode for debugging
- `main_live2d.py` - Live2D overlay only mode

### 2. **requirements.txt Updated**
Removed unavailable package `pycubism` and updated dependencies:
- ✅ Added: `groq`, `google-generativeai`, `openai` (AI APIs)
- ✅ Added: `pydub`, `aiofiles`, `qasync` (utilities)
- ✅ Removed: `pycubism` (not available on PyPI - manual install required)
- ⚠️ Note: `xdotool` is a system package, install via `sudo pacman -S xdotool`

### 3. **PyQt6-WebEngine Issue**
⚠️ **Disk Space Warning**: Your system has only 205MB free space.
PyQt6-WebEngine requires ~300MB. Please free up space first:

```bash
# Clean pip cache
pip cache purge

# Remove unused packages
pip uninstall PyQt6-WebEngine  # if partially installed

# Free disk space (remove old logs, temp files, etc.)
sudo pacman -Sc  # Clean pacman cache
```

Then install:
```bash
pip install PyQt6-WebEngine
```

---

## 🔧 Installation Steps

### Step 1: Install System Dependencies (Arch Linux)
```bash
sudo pacman -S xdotool wmctrl scrot
```

### Step 2: Install Python Dependencies
```bash
cd /path/to/AICOMPANION
pip install -r requirements.txt
```

### Step 3: Manual Live2D Setup (Required for Avatar)
Since `pycubism` is not on PyPI, you have two options:

**Option A: Use Emoji Fallback (No Live2D)**
The app will work with emoji expressions instead of Live2D avatar.

**Option B: Manual Live2D SDK Installation**
1. Download Live2D Cubism SDK from: https://www.live2d.com/en/download/cubism-sdk/
2. Extract to `assets/cubism-sdk/`
3. Follow SDK instructions for Python binding

### Step 4: Download Live2D Model
1. Get model from Booth: https://booth.pm/jp/items/4711410
2. Extract to: `assets/models/kira_live2d/`

### Step 5: Configure Environment
```bash
cp .env.example .env
# Edit .env and add your API keys:
# - GROQ_API_KEY (free at https://console.groq.com)
# - GEMINI_API_KEY (free at https://aistudio.google.com)
```

### Step 6: Run the Application
```bash
# Recommended: Dashboard mode
python main_dashboard.py

# Or CLI mode (no GUI)
python main_cli.py

# Or Live2D only mode
python main_live2d.py
```

---

## 🐛 Troubleshooting

### Error: "No module named 'qasync'"
```bash
pip install qasync
```

### Error: "Cannot open display"
Make sure you're running on X11, not Wayland:
```bash
export GDK_BACKEND=x11
python main_dashboard.py
```

### Error: "xdotool not found"
```bash
sudo pacman -S xdotool
```

### Error: "No space left on device"
```bash
# Check disk usage
df -h

# Clean up
pip cache purge
sudo pacman -Sc
rm -rf ~/.cache/pip
```

---

## 📋 Current File Structure
```
AICOMPANION/
├── main.py                 # Core application class
├── main_dashboard.py       # ✅ NEW: Dashboard entry point
├── main_cli.py             # ✅ NEW: CLI entry point
├── main_live2d.py          # ✅ NEW: Live2D-only entry point
├── requirements.txt        # ✅ UPDATED: Fixed dependencies
├── .env.example            # Environment template
├── README.md               # Documentation
├── progress.md             # Development progress
└── companion/              # Main package
    ├── desktop/
    │   └── live2d_overlay.py  # Live2D rendering
    ├── brain/              # AI logic
    ├── senses/             # Input handling
    └── ...
```

---

## ✨ What's Working Now
- ✅ All entry point files created
- ✅ requirements.txt fixed (no pycubism)
- ✅ Groq, Gemini, OpenAI clients ready
- ✅ Desktop automation modules present
- ✅ Live2D overlay code exists (needs SDK)

## ⚠️ What Needs Attention
- 🔴 Disk space low (205MB free) - need 300MB+ for PyQt6-WebEngine
- 🔴 Live2D Cubism SDK not installed (optional, emoji fallback available)
- 🔴 Live2D model not downloaded (optional for avatar)
- 🔴 API keys not configured in .env

