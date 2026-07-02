#!/usr/bin/env bash
# run.sh
# Main runner wrapper for MyCompanion framework.

set -e

# Đảm bảo đang ở đúng thư mục chứa dự án
cd "$(dirname "$0")"

# Kiểm tra sự tồn tại của tệp .env
if [ ! -f ".env" ]; then
    echo "Lỗi: Chưa có tệp cấu hình .env."
    echo "Vui lòng chạy './setup_arch.sh' trước hoặc tạo tệp .env."
    exit 1
fi

# Chạy tệp tin chính
echo "Đang khởi chạy MyCompanion..."
python main.py
