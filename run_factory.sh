#!/bin/bash

# ==============================================================================
# Unified AI Software Factory Startup Script (Tối ưu hóa hiển thị Log)
# ==============================================================================

# Khai báo mã màu ANSI hiển thị thông tin trực quan
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Tạo thư mục workspace nếu chưa có và chỉ định tệp log tạm thời
mkdir -p workspace
LOG_FILE="workspace/startup.log"
echo "--- Khởi tạo tiến trình lúc $(date) ---" > "$LOG_FILE"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${GREEN}🚀 UNIFIED AI SOFTWARE FACTORY BOOTSTRAP${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Kiểm tra cấu hình môi trường .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[1/4] ⚠️  Tạo tệp cấu hình từ .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}      ✅ Đã tạo tệp .env thành công.${NC}"
else
    echo -e "${GREEN}[1/4] ✅ Cấu hình .env đã sẵn sàng.${NC}"
fi

# 2. Thiết lập Python venv & Cài đặt requirements
echo -e "${BLUE}[2/4] ⚙️  Đang cài đặt môi trường ảo & dependencies Python (pip)...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv >> "$LOG_FILE" 2>&1
fi

# Kích hoạt venv
source venv/bin/activate

# Nâng cấp pip và cài đặt dependencies không hiển thị logs rác
if pip install --upgrade pip >> "$LOG_FILE" 2>&1 && \
   pip install -r requirements.txt >> "$LOG_FILE" 2>&1; then
    echo -e "${GREEN}      ✅ Dependencies Backend đã cài đặt thành công.${NC}"
else
    echo -e "${RED}      ❌ Lỗi: Cài đặt dependencies Backend thất bại!${NC}"
    echo -e "${RED}      👉 Chi tiết lỗi lưu tại: $LOG_FILE${NC}"
    exit 1
fi

# 3. Cài đặt Node packages & Biên dịch đóng gói Frontend
echo -e "${BLUE}[3/4] ⚙️  Đang cài đặt packages & biên dịch giao diện (npm)...${NC}"
if [ -d "frontend" ]; then
    cd frontend
    
    # Chạy npm install và npm run build ẩn toàn bộ logs thông báo và warning
    if npm install --no-audit --no-fund --silent >> "../$LOG_FILE" 2>&1 && \
       npm run build --silent >> "../$LOG_FILE" 2>&1; then
        cd ..
        echo -e "${GREEN}      ✅ Giao diện tĩnh Frontend được đóng gói thành công tại frontend/dist.${NC}"
    else
        cd ..
        echo -e "${RED}      ❌ Lỗi: Cài đặt hoặc biên dịch Frontend thất bại!${NC}"
        echo -e "${RED}      👉 Chi tiết lỗi lưu tại: $LOG_FILE${NC}"
        exit 1
    fi
else
    echo -e "${RED}      ❌ Lỗi: Không tìm thấy thư mục frontend!${NC}"
    exit 1
fi

# 4. Khởi chạy Server
echo -e "${BLUE}[4/4] 🚀 Khởi động dịch vụ API Server...${NC}"
echo -e "${GREEN}----------------------------------------------------------------------${NC}"
echo -e "${GREEN}💡 Hệ thống đã hoạt động!${NC}"
echo -e "${GREEN}🔗 Dashboard UI: http://localhost:8000${NC}"
echo -e "${GREEN}🔗 Swagger APIs: http://localhost:8000/docs${NC}"
echo -e "${GREEN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}📢 Đang khởi chạy uvicorn server... (Nhấn Ctrl+C để dừng)${NC}\n"

# Khởi chạy uvicorn
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
