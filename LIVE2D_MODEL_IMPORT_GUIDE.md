# 📥 Hướng Dẫn Import Model Live2D cho KIRA

## 🎯 Yêu cầu cấu trúc thư mục

```
/workspace/
└── assets/
    └── models/
        └── kira_live2d/
            ├── model.json              # BẮT BUỘC - File cấu hình chính
            ├── textures/               # BẮT BUỘC - Thư mục texture
            │   ├── texture_00.png
            │   └── ...
            ├── motions/                # Tùy chọn - Animation
            │   ├── idle.mtn3
            │   └── talk.mtn3
            └── physics.json            # Tùy chọn - Physics settings
```

## 📋 Các file cần thiết

### 1. model.json (BẮT BUỘC)
File cấu hình chính mô tả tất cả tài nguyên của model.

**Ví dụ nội dung:**
```json
{
  "Version": 3,
  "FileReferences": {
    "Moc": "model.moc3",
    "Textures": [
      "textures/texture_00.png",
      "textures/texture_01.png"
    ],
    "Physics": "physics.json",
    "DisplayInfo": "display_info.json",
    "Motions": {
      "Idle": [
        {"File": "motions/idle.mtn3", "FadeInTime": 0.5, "FadeOutTime": 0.5}
      ],
      "TapBody": [
        {"File": "motions/tap_body.mtn3", "Sound": "sounds/tap.mp3"}
      ]
    }
  },
  "Groups": [
    {
      "Target": "Parameter",
      "Name": "EyeBlink",
      "Ids": ["PARAM_EYE_L_OPEN", "PARAM_EYE_R_OPEN"]
    }
  ],
  "HitAreas": [
    {"Id": "HitHead", "Name": "Head"},
    {"Id": "HitBody", "Name": "Body"}
  ]
}
```

### 2. File .moc3 (BẮT BUỘC)
File binary chứa dữ liệu model Live2D Cubism 3.

**Tên thường gặp:**
- `model.moc3`
- `character.moc3`
- `<tên_model>.moc3`

### 3. Textures (BẮT BUỘC)
Các file PNG chứa texture cho model.

**Vị trí:** `textures/` folder
**Định dạng:** `.png` với alpha channel (trong suốt)

### 4. File vật lý và animation (Tùy chọn)
- `physics.json` - Cài đặt vật lý cho tóc, quần áo
- `*.mtn3` hoặc `*.motion3.json` - Animation motions
- `display_info.json` - Thông tin hiển thị các parts

## 🔧 Cách đặt tên file

### ✅ Đúng (KIRA sẽ nhận diện):
```
assets/models/kira_live2d/
├── model.json              ← Tên chuẩn
├── character.moc3          ← Hoặc bất kỳ tên nào, chỉ cần khai báo trong model.json
├── textures/
│   └── texture_00.png      ← Đánh số tăng dần
└── motions/
    └── idle.mtn3
```

### ❌ Sai (Sẽ không hoạt động):
```
assets/models/kira_live2d/
├── KIRA.model3.json        ← SAI: Phải là model.json
├── live2d.moc3             ← OK nếu khai báo đúng trong model.json
└── Texture/                ← SAI: Phải là textures/ (thường case-sensitive)
```

## 📦 Quy trình import từ Booth PM

### Bước 1: Tải model từ Booth
1. Truy cập: https://booth.pm/jp/items/4711410
2. Đăng nhập và mua/tải về
3. File tải về thường là `.zip`

### Bước 2: Giải nén và trích xuất
```bash
# Giải nén file zip
unzip booth_4711410.zip -o downloaded_model/

# Tìm file .model3.json chính
find downloaded_model/ -name "*.model3.json"

# Tạo thư mục đích
mkdir -p assets/models/kira_live2d
```

### Bước 3: Sao chép files
```bash
# Copy file cấu hình (đổi tên thành model.json)
cp downloaded_model/path/to/model.model3.json assets/models/kira_live2d/model.json

# Copy thư mục textures
cp -r downloaded_model/path/to/textures/ assets/models/kira_live2d/

# Copy file .moc3
cp downloaded_model/path/to/*.moc3 assets/models/kira_live2d/

# Copy motions (nếu có)
cp -r downloaded_model/path/to/motions/ assets/models/kira_live2d/
```

### Bước 4: Kiểm tra cấu trúc
```bash
tree assets/models/kira_live2d/
# Hoặc
ls -laR assets/models/kira_live2d/
```

## 🔍 Debug: Kiểm tra model đã hợp lệ chưa

### Python script kiểm tra:
```python
from pathlib import Path
import json

model_dir = Path("assets/models/kira_live2d")

# Kiểm tra model.json
model_file = model_dir / "model.json"
if not model_file.exists():
    print("❌ model.json not found!")
else:
    print("✅ model.json exists")
    
    # Đọc và validate
    with open(model_file) as f:
        config = json.load(f)
    
    # Kiểm tra moc file
    moc_path = config.get("FileReferences", {}).get("Moc")
    if moc_path and (model_dir / moc_path).exists():
        print(f"✅ Moc file found: {moc_path}")
    else:
        print(f"❌ Moc file not found: {moc_path}")
    
    # Kiểm tra textures
    textures = config.get("FileReferences", {}).get("Textures", [])
    for tex in textures:
        if (model_dir / tex).exists():
            print(f"✅ Texture found: {tex}")
        else:
            print(f"❌ Texture missing: {tex}")
```

### Chạy thử:
```bash
python main_live2d.py
```

**Log mong đợi:**
```
🚀 Starting KIRA Desktop Companion (Live2D Only Mode)...
============================================================
Live2D model loaded: assets/models/kira_live2d/model.json
Live2D Overlay initialized at (100, 100)
```

**Log lỗi thường gặp:**
```
⚠️  Live2D model directory not found: assets/models/kira_live2d
→ Tạo thư mục và copy files vào

⚠️  model.json not found in assets/models/kira_live2d
→ Đổi tên file .model3.json thành model.json

[JS ERROR] Failed to load model: 404
→ Kiểm tra đường dẫn texture trong model.json
```

## 🛠️ Xử lý lỗi thường gặp

### Lỗi 1: CORS khi load local files
**Triệu chứng:** Console báo "Access-Control-Allow-Origin" error

**Giải pháp:** Code đã xử lý bằng cách:
```python
self.web_view.setHtml(html_content, QUrl.fromLocalFile(str(self.model_path)))
```

### Lỗi 2: WebGL not supported
**Triệu chứng:** Hiện message "WebGL not supported"

**Giải pháp:**
- Cập nhật driver GPU
- Enable hardware acceleration trong PyQt6
- Thử chạy trên máy khác có GPU tốt hơn

### Lỗi 3: Model load nhưng không hiển thị
**Triệu chứng:** Không có lỗi nhưng màn hình trống

**Kiểm tra:**
1. Window flags có đúng không?
2. Background có transparent không?
3. JS console có lỗi gì không?

**Debug:**
```python
# Thêm logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Mẫu model.json đơn giản

Nếu bạn tự tạo model, đây là template tối thiểu:

```json
{
  "Version": 3,
  "FileReferences": {
    "Moc": "my_model.moc3",
    "Textures": [
      "textures/texture_00.png"
    ]
  },
  "Groups": [],
  "HitAreas": []
}
```

---

**Cập nhật:** 2024-01-XX
**Tác giả:** KIRA Development Team
