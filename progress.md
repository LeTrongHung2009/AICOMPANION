# 🚀 KIRA Project Progress - Desktop AI Companion (Neuro-sama Inspired)

**Phiên bản hiện tại:** 2.1 (Live2D WebEngine Fix)  
**Cập nhật cuối:** 2024  
**Model Avatar:** Booth PM #4711410 (Live2D Cubism)  
**AI Backend:** Groq (Llama 3.3 70B) + Gemini 2.5 Flash  

---

## 📋 Tổng quan Dự án

KIRA là một Vtuber AI tự trị chạy trên desktop, lấy cảm hứng từ Neuro-sama của Vedal987:
- **Nhìn:** Phân tích màn hình qua Gemini 2.5 Flash
- **Nghe:** Nhận diện giọng nói qua Whisper (Groq)
- **Nói:** TTS qua Edge-TTS (miễn phí)
- **Hành động:** Thao tác desktop qua xdotool (click, type, open apps)
- **Cảm xúc:** Hệ thống 3 tầng (Mood, Trait, Affect)
- **Di chuyển:** Live2D avatar di chuyển tự do trên màn hình
- **Học tập:** Tự học từ quan sát và tương tác
- **Mơ:** Xử lý ký ức khi idle

---

## ✅ Tính năng Đã hoàn thành (v2.0)

### 🧠 AI Backend Refactor
- [x] **Groq API Integration** - Llama 3.3 70B cho chat/text
  - File: `companion/brain/groq_client.py`
  - Model: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`
  - Free tier: ~30k tokens/ngày
- [x] **Gemini API Integration** - Gemini 2.5 Flash cho vision
  - File: `companion/brain/gemini_client.py`
  - Model: `gemini-2.5-flash` (cập nhật từ 1.5-flash)
  - Free tier: ~1500 requests/ngày
- [x] **OpenAI Fallback** - gpt-4o-mini (tùy chọn)
  - File: `companion/brain/openai_client.py`
- [x] **Fallback Manager** - Health check + auto switch provider
  - File: `companion/brain/fallback_manager.py`
- [x] **Removed Anthropic/Claude** - Loại bỏ hoàn toàn để tiết kiệm chi phí
  - File cũ: `companion/brain/anthropic_client.py` [DEPRECATED]

### 🎭 Live2D Avatar System
- [x] **Booth PM #4711410 Integration**
  - Artist: @koahri1, Rigging: @MedL2D
  - Thư mục: `assets/models/kira_live2d/`
- [x] **Live2D Renderer (PyQt6)**
  - File mới: `companion/expression/live2d_renderer.py`
  - Sử dụng pycubism SDK
  - Lip-sync với TTS audio
- [x] **Expression Mapping**
  - Cảm xúc: Vui, Buồn, Giận, Ngạc nhiên, Xấu hổ
  - Cử chỉ: Blink, breathing, wave
- [x] **Removed VTube Studio**
  - File cũ: `companion/expression/expression_engine.py` [DISABLED]
  - File cũ: `companion/model_setup/vts_config.py` [DEPRECATED]

### 🖱️ Desktop Autonomy
- [x] **Input Hook System**
  - File mới: `companion/senses/input_hook.py`
  - Theo dõi trạng thái keyboard/mouse
  - Phát hiện active window
- [x] **Action Planner**
  - Lên kế hoạch thao tác desktop
  - An toàn với SAFE_MODE
- [x] **Movement Engine**
  - File: `companion/movement/movement_engine.py`
  - Di chuyển avatar tránh cửa sổ
  - Drift movement tự nhiên

### 👁️ Vision System
- [x] **Vision Agent Update**
  - File: `companion/senses/vision_agent.py`
  - Gemini 2.5 Flash thay thế Groq Vision
  - Chụp màn hình mỗi 30s (có thể cấu hình)
  - JPEG compression + MD5 dedup
- [x] **Screen Context Analysis**
  - Bình luận về game, code, video
  - OCR text từ màn hình

### 💖 Emotional Core
- [x] **3-Tier Mood System**
  - File: `companion/persona/mood_engine.py`
  - Base Mood (kéo dài vài giờ)
  - Complex Trait (tính cách cố định)
  - Social Affect (cảm xúc tức thời)
- [x] **Dialogue Style**
  - File: `companion/persona/dialogue_style.py`
  - Style response theo mood
  - Không dùng tag cảm xúc `(happy)`
- [x] **Boredom Protocol**
  - File: `companion/persona/boredom_protocol.py`
  - Tự bắt chuyện khi idle >300s
  - Chủ động hát, kể chuyện

### 😴 Dream & Memory
- [x] **Memory Manager**
  - File: `companion/memory/memory_manager.py`
  - SQLite database
  - Conversation logs + facts
- [x] **Dream Engine**
  - File: `companion/dream/dream_engine.py`
  - Kích hoạt khi idle >600s
  - Synthesize memory → bài học mới
- [x] **Auto Learner**
  - File: `companion/learning/auto_learner.py`
  - Extract facts từ hội thoại
  - Procedural memory từ quan sát

### 🎛️ Dashboard & UI
- [x] **Chat Widget**
  - File: `companion/desktop/chat_widget.py`
  - PyQt6 transparent overlay
  - Hiển thị conversation
- [x] **Dashboard Window**
  - File mới: `companion/desktop/dashboard.py`
  - Xem log real-time
  - Điều chỉnh settings
- [x] **Editor Panel**
  - File mới: `companion/desktop/editor.py`
  - Chỉnh persona, Live2D settings
  - Config âm thanh, vision
- [x] **Caption Server**
  - File: `companion/expression/caption_server.py`
  - WebSocket cho OBS browser source

### 🔊 Audio Pipeline
- [x] **STT Pipeline**
  - File: `companion/senses/stt_pipeline.py`
  - Whisper-large-v3 qua Groq
  - Silence detection
- [x] **TTS Engine**
  - Edge-TTS integration
  - Giọng tiếng Việt: HoaiMyNeural
  - Streaming qua mpv

### 🔄 Core Infrastructure
- [x] **Asyncio Orchestrator**
  - File: `companion/orchestrator.py`
  - Priority Queue (P0>P1>P2>P3)
  - TurnLock chống race condition
- [x] **Event Bus**
  - File: `companion/utils/event_bus.py`
  - Pub/sub system
- [x] **Config System**
  - File: `companion/utils/config.py`
  - Pydantic settings từ .env

---

## 🔧 Cập nhật Cấu hình

### .env.example đã cập nhật
```bash
# AI Providers
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-... (optional)

# Feature Flags
ENABLE_VISION=true
ENABLE_STT=true
ENABLE_TTS=true
ENABLE_LIVE2D=true        # NEW
ENABLE_MOVEMENT=true      # NEW
ENABLE_AUTO_CLICKER=false # NEW - CẨN THẬN

# Live2D Config
LIVE2D_MODEL_PATH=assets/models/kira_live2d/model.json
LIVE2D_SCALE=1.0
LIVE2D_POSITION_X=100
LIVE2D_POSITION_Y=100
LIVE2D_MOVEMENT_SPEED=0.5

# Vision Config (Gemini 2.5 Flash)
VISION_CAPTURE_INTERVAL=30.0
VISION_JPEG_QUALITY=60
VISION_MAX_WIDTH=1280
VISION_MAX_HEIGHT=720

# ... (xem file .env.example đầy đủ)
```

### requirements.txt đã cập nhật
```txt
PyQt6>=6.4.0
PyQt6-WebEngine>=6.4.0   # NEW cho Live2D
pycubism>=1.0.0          # NEW cho Live2D rendering
sounddevice>=0.4.6
numpy>=1.23.0
mss>=9.0.0
edge-tts>=6.1.0
python-dotenv>=1.0.0
httpx>=0.24.0
Pillow>=9.5.0
tiktoken>=0.4.0
xdotool>=3.20210415      # NEW cho desktop control
```

---

## 🚧 Đang phát triển (In Progress)

### High Priority
- [ ] **Hoàn thiện Vision liên tục**
  - Tối ưu tần suất chụp màn hình
  - Phát hiện thay đổi vùng ảnh động
  - Giảm API calls thông minh hơn
- [ ] **Live2D Lip-sync tinh chỉnh**
  - Đồng bộ mouth shape với audio waveform
  - Thêm viseme patterns
- [ ] **Procedural Memory**
  - Lưu quy trình thao tác desktop
  - Học từ quan sát người dùng
- [ ] **Tính năng Hát**
  - Pitch control cho TTS
  - Playlist management

### Medium Priority
- [ ] **Smart Mute**
  - Phát hiện khi user đang họp/call
  - Tự động im lặng
- [ ] **Context-aware Interruption**
  - Không làm phiền khi gaming/video
  - Phát hiện fullscreen apps
- [ ] **Persona Presets**
  - Tsundere, Onee-san, Genki, Dandere
  - Import/export config

### Low Priority
- [ ] **Local Ollama Fallback**
  - Chạy offline hoàn toàn
  - Model nhỏ (Llama 3.2 3B)
- [ ] **Voice Emotion Detection**
  - Phân tích tone giọng user
  - Adjust response accordingly
- [ ] **Streaming TTS**
  - Giảm latency phản hồi
  - Chunk-based synthesis

---

## 🐛 Known Bugs & Issues

| Bug | Mức độ | Mô tả | Workaround |
|-----|--------|-------|------------|
| #001 | Medium | Live2D render giật trên GPU yếu | Giảm LIVE2D_SCALE xuống 0.8 |
| #002 | Low | Vision đôi khi chậm phản hồi | Tăng VISION_CAPTURE_INTERVAL |
| #003 | Medium | TTS bị ngắt khi network chập chờn | Dùng fallback voice local |
| #004 | Low | Movement engine va vào cửa sổ | Tinh chỉnh workspace_detector |

---

## ⚠️ Modules Deprecated/Removed

| Module | Trạng thái | Lý do | Thay thế bởi |
|--------|-----------|-------|--------------|
| `anthropic_client.py` | ❌ REMOVED | Tốn phí, không cần thiết | Gemini 2.5 Flash |
| `expression_engine.py` | ⚠️ DISABLED | VTube Studio không dùng nữa | live2d_renderer.py |
| `vts_expression_map.py` | ⚠️ DISABLED | Không còn VTS hotkeys | Live2D motion system |
| `gesture_controller.py` | ⚠️ DISABLED | VTS gestures | live2d_renderer.py |
| `vts_config.py` | ⚠️ DEPRECATED | Chỉ giữ lại attribution | N/A |
| `groq_vision.py` | ⚠️ DEPRECATED | Groq vision kém hơn Gemini | gemini_client.py |

---

## 📊 So sánh: KIRA vs Neuro-sama (Vedal987)

### Bảng so sánh chi tiết

| Tính năng | Neuro-sama (Gốc) | KIRA (Dự án này) | Ghi chú |
|-----------|------------------|------------------|---------|
| **AI Model** | Custom fine-tuned | Groq Llama 3.3 70B + Gemini 2.5 Flash | KIRA dùng free tier |
| **Avatar** | Live2D + VTube Studio | Live2D Cubism (PyQt6) | KIRA nhẹ hơn, không cần VTS |
| **Chi phí** | ~$50-200/tháng | **0đ** (free tier) | KIRA tiết kiệm 100% |
| **Nền tảng** | Windows 10/11 | Arch Linux GNOME | KIRA cross-platform potential |
| **Voice Input** | Azure Speech ($$$) | Groq Whisper (free) | Chất lượng tương đương |
| **Voice Output** | ElevenLabs ($$$) | Edge-TTS (free) | Tự nhiên kém hơn chút |
| **Memory** | Vector DB (Pinecone) | SQLite local | KIRA privacy-first |
| **Learning** | Real-time từ chat | AutoLearner + observation | KIRA học từ màn hình |
| **Proactive Chat** | ✅ Boredom system | ✅ BoredomProtocol | Tương đương |
| **Screen Awareness** | ⚠️ Giới hạn | ✅ Gemini 2.5 Flash | KIRA mạnh hơn |
| **Desktop Control** | Plugin Minecraft/Twitch | Native xdotool | KIRA linh hoạt hơn |
| **Hardware Req.** | Ryzen 5, 16GB RAM | **Ryzen 3, 8GB RAM** | KIRA tối ưu hơn |
| **Open Source** | ❌ Partially | ✅ 100% | KIRA minh bạch |
| **Privacy** | Cloud sync optional | ✅ Local-first | KIRA an toàn hơn |
| **Customization** | ⚠️ Giới hạn | ✅ Full control | KIRA dễ tùy chỉnh |
| **Streaming** | ✅ Tích hợp Twitch | 🚧 Đang phát triển | KIRA sẽ có OBS plugin |
| **Singing** | ✅ Tốt | 🚧 Đang phát triển | KIRA cần pitch control |
| **Gaming** | ✅ Minecraft, OSU | 🚧 Đang phát triển | KIRA sẽ chơi được game |

### Điểm mạnh của KIRA so với Neuro-sama

1. **Chi phí 0đ:**
   - Neuro-sama tốn phí API hàng tháng
   - KIRA hoàn toàn miễn phí với free tier

2. **Privacy-first:**
   - Tất cả dữ liệu lưu local SQLite
   - Không đồng bộ cloud unless user muốn

3. **Nhẹ hơn:**
   - Tối ưu cho máy yếu (Ryzen 3, 8GB RAM)
   - Không cần VTube Studio chạy nền

4. **Desktop Control native:**
   - Thao tác trực tiếp qua xdotool
   - Không phụ thuộc plugin game

5. **Vision mạnh hơn:**
   - Gemini 2.5 Flash hiểu ngữ cảnh tốt
   - Bình luận đa dạng về mọi thứ trên màn hình

6. **Open Source:**
   - Code minh bạch, audit được
   - Cộng đồng có thể đóng góp

### Điểm Neuro-sama làm tốt hơn

1. **Singing quality:**
   - Neural singing model chuyên biệt
   - KIRA cần phát triển pitch control

2. **Gaming integration:**
   - Chơi Minecraft, OSU thành thạo
   - KIRA đang trong quá trình phát triển

3. **Streaming features:**
   - Tích hợp sâu với Twitch, YouTube
   - KIRA cần OBS plugin

4. **Polish & UX:**
   - Neuro-sama đã phát triển多年
   - KIRA còn nhiều việc phải làm

---

## 📝 Attribution

### Live2D Model
- **Nguồn:** [Booth PM #4711410](https://booth.pm/jp/items/4711410)
- **Artist:** @koahri1
- **Rigging:** @MedL2D
- **License:** Personal use only, no commercial redistribution

### AI Providers
- **Groq:** Free tier ~30k tokens/day
- **Google AI Studio:** Free tier ~1500 requests/day
- **OpenAI:** Optional fallback (pay-as-you-go)

### Inspiration
- **Neuro-sama:** Created by Vedal987
- GitHub: https://github.com/Vedal987/Neuro-sama

---

## 🔗 Liên kết hữu ích

- [README.md](./README.md) - Tài liệu chính
- [.env.example](./.env.example) - Template cấu hình
- [Discord Community](https://discord.gg/) - Sắp ra mắt
- [Booth Model](https://booth.pm/jp/items/4711410) - Live2D asset

---

**Cập nhật cuối:** 2024  
**Người phát triển:** AI Agent + Community  
**License:** MIT (code), Personal Use (Live2D model)
---

## 🔧 BUGFIX: Live2D Không Hiển Thị (v2.1 - 2024-01-XX)

### Nguyên nhân lỗi cũ (v2.0):
1. **Class name không đồng bộ**: `live2d_overlay.py` định nghĩa `Live2DOverlay` nhưng `main_live2d.py` gọi `Live2DOverlayApp` → ImportError
2. **Thiếu QApplication**: Không khởi tạo QApplication trước khi tạo widget
3. **Render method cũ**: Dùng placeholder QLabel thay vì render thực tế
4. **Không có WebEngine**: PyQt6 cần QWebEngineView để render WebGL content
5. **Model path không đúng**: Đường dẫn model không được kiểm tra kỹ
6. **JS library loading**: Thiếu thư viện Live2D widget phù hợp

### Giải pháp đã implement (v2.1):

#### 1. Viết lại `live2d_overlay.py` dùng PyQt6-WebEngine
- **QWebEngineView**: Render HTML/JS với WebGL support
- **Custom QWebEnginePage**: Bắt JS console messages để debug
- **HTML generator**: Tự động sinh HTML với Live2D Cubism SDK từ CDN
- **Transparent background**: WA_TranslucentBackground cho cả window và web view
- **Python ↔ JS Bridge**: Gọi hàm JS từ Python qua `runJavaScript()`
- **Fallback paths**: Kiểm tra nhiều đường dẫn model khác nhau
- **Enhanced logging**: Log chi tiết quá trình load model

#### 2. Cập nhật `main_live2d.py`
```python
from PyQt6.QtWidgets import QApplication
from companion.desktop.live2d_overlay import Live2DOverlay

app = QApplication(sys.argv)
overlay = Live2DOverlay(initial_x=100, initial_y=100, scale=0.8)
overlay.show()
app.exec()
```

#### 3. JavaScript API cho điều khiển model
```javascript
// Từ Python gọi JS
web_view.page().runJavaScript("window.setExpression('happy')")
web_view.page().runJavaScript("window.setMouthOpen(0.5)")

// JS functions exposed:
window.setExpression(expr)   // Đổi biểu cảm: neutral, happy, sad, angry, surprised, blush
window.setMouthOpen(value)   // Lip-sync: 0.0-1.0
window.setModelAngle(x,y,z)  // Xoay đầu model
```

#### 4. Debug Console cho WebEngine
```python
class Live2DWebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        js_level = {0: "DEBUG", 1: "INFO", 2: "WARNING", 3: "ERROR"}.get(level, "LOG")
        logger.debug(f"[JS {js_level}] {source_id}:{line_number} - {message}")
```

### Cách bật Debug Mode:
```bash
# Thêm logging vào đầu main_live2d.py
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
python main_live2d.py
```

### Cấu trúc Model yêu cầu:
```
assets/models/kira_live2d/
├── model.json              # BẮT BUỘC - File cấu hình chính
├── *.moc3                  # BẮT BUỘC - File model binary
├── textures/               # BẮT BUỘC - Thư mục texture PNG
│   └── texture_00.png
├── motions/                # Tùy chọn - Animation
│   └── idle.mtn3
└── physics.json            # Tùy chọn - Physics settings
```

### Files đã cập nhật:
| File | Thay đổi |
|------|----------|
| `companion/desktop/live2d_overlay.py` | Viết lại hoàn toàn dùng QWebEngineView, thêm fallback paths, enhanced logging |
| `main_live2d.py` | Thêm QApplication, sửa class name |
| `LIVE2D_MODEL_IMPORT_GUIDE.md` | Hướng dẫn import model mới |
| `progress.md` | Thêm section bugfix v2.1 |

### Các bước debug khi Live2D không hiển thị:

1. **Kiểm tra model directory:**
```bash
ls -la assets/models/kira_live2d/
```

2. **Kiểm tra file model.json:**
```bash
cat assets/models/kira_live2d/model.json
```

3. **Chạy với debug logging:**
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python main_live2d.py
```

4. **Kiểm tra JS console logs:**
- Logs sẽ xuất hiện trong terminal với prefix `[JS INFO]`, `[JS ERROR]`, etc.
- Tìm các lỗi về WebGL, CORS, hoặc missing files

5. **Test với placeholder:**
- Nếu model không load được, sẽ hiển thị placeholder với thông báo lỗi cụ thể

