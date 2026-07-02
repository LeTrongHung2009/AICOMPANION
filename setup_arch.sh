#!/usr/bin/env bash
# setup_arch.sh
# Automated dependency installer for MyCompanion on Arch Linux.

set -e

echo "=== Cấu hình môi trường MyCompanion cho Arch Linux ==="

# 1. Kiểm tra quyền/gói hệ thống qua pacman
echo "1. Đang kiểm tra các gói phụ thuộc hệ thống (pacman)..."
REQUIRED_PACKAGES=(mpv portaudio xdotool python-pip)
MISSING_PACKAGES=()

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if ! pacman -Qi "$pkg" &>/dev/null; then
        MISSING_PACKAGES+=("$pkg")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo "Các gói còn thiếu: ${MISSING_PACKAGES[*]}"
    echo "Đang cài đặt qua pacman (yêu cầu mật khẩu sudo)..."
    sudo pacman -S --needed --noconfirm "${MISSING_PACKAGES[@]}"
else
    echo "Tất cả gói hệ thống cần thiết đã được cài đặt."
fi

# 2. Cài đặt Python requirements
echo "2. Đang cài đặt thư viện Python..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Lỗi: Không tìm thấy requirements.txt"
    exit 1
fi

# 3. Tạo môi trường cấu hình mẫu
if [ ! -f ".env" ]; then
    echo "3. Khởi tạo cấu hình mặc định .env..."
    cp .env.example .env
    echo "Đã tạo tệp cấu hình .env. Vui lòng thêm khoá API trước khi chạy."
fi

echo "=== Quá trình cài đặt hoàn tất! ==="
