# MyCompanion Framework

AI Desktop Companion chạy hoàn toàn Local, không streaming, tối ưu hóa cho cấu hình phần cứng tối thiểu (AMD Ryzen 3, AMD Radeon Onboard, 8GB RAM) trên hệ điều hành **Arch Linux GNOME**.

## 🧠 Sơ đồ Kiến trúc & Vòng đời

```
+-----------------------------------------------------------------------------------+
|                              AsyncioOrchestrator                                  |
|                                                                                   |
|  [PriorityQueue]                                                                  |
|   P0: User Text  --->  [TurnLock]  --->  [AI Cortex] ---> [TTS/VTS Expressions]   |
|   P1: Voice input       (Lock Guard)      - Groq Llama 3    - VTS WebSockets      |
|   P2: Vision VLM                          - Fallback (OAI)  - edge-tts via mpv    |
|   P3: Boredom                                                                     |
+-----------------------------------------------------------------------------------+
```

### Quy trình Vòng đời (Life Cycle)

1. **Khởi chạy (Startup):**
   - Đọc tệp cấu hình `.env` và cơ sở dữ liệu `SQLite`.
   - Hiển thị bản quyền ghi công (Attribution) bắt buộc đối với mô hình Live2D Booth PM #4711410.
   - Bắt đầu các kết nối dịch vụ nền (VTS WebSocket, Vision Agent, STT, Boredom Protocol).
2. **Xử lý Tương tác (Interaction):**
   - Người dùng nhập text hoặc nói qua micro (được sounddevice lưu WAV ngắn -> Whisper).
   - Vision Agent chụp màn hình bằng `mss`, nén ảnh JPEG 60%, lọc trùng bằng mã băm MD5.
   - Toàn bộ được định tuyến qua `PriorityQueue` và khóa đồng bộ `TurnLock`.
3. **Mơ (Dream Engine):**
   - Kích hoạt khi không tương tác quá 600 giây.
   - Tiến hành gộp các dữ liệu chat trong ngày, phân tích và lưu vào cơ sở dữ liệu dưới dạng "Memory".
   - Tự động sinh chủ đề ngày tiếp theo.

## 🎨 Ghi công Bản quyền bắt buộc (Attribution)

Hệ thống được thiết kế tích hợp với mô hình Live2D:
- **Nguồn:** [Booth PM #4711410](https://booth.pm/en/items/4711410)
- **Tác giả Vẽ (Artist):** `@koahri1`
- **Rigging Live2D:** `@MedL2D`
- *Lưu ý pháp lý:* Nghiêm cấm phân phối lại, bán lại hoặc sửa đổi mô hình để thương mại hóa mà không có sự cho phép từ các tác giả.

## 🛠️ Cài đặt & Khởi chạy trên Arch Linux

### 1. Cài đặt các gói hệ thống cần thiết

```bash
sudo pacman -S python-pip mpv portaudio xdotool
```

### 2. Cài đặt Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu hình khóa API

Sao chép `.env.example` thành `.env` và nhập khóa API của bạn:

```bash
cp .env.example .env
```

### 4. Khởi chạy ứng dụng

Đảm bảo **VTube Studio** đã được chạy trước tại cổng WebSocket công khai `8001`:

```bash
python main.py
```
# AICOMPANIONAI
# AICOMPANIONAI
