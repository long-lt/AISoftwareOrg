# AI Software Factory Dashboard Platform

Bảng điều khiển quản trị (Dashboard Command Center) cao cấp dành cho hệ thống **AI Software Factory Platform**, được xây dựng trên nền tảng **Vite** sử dụng kiến trúc giao diện **Modular Vanilla JS** cực kỳ sạch sẽ, tối ưu hiệu năng và dễ dàng mở rộng.

Hệ thống hỗ trợ quản lý vòng đời phân phối phần mềm tích hợp AI: Projects, Pipelines, AI Models, AI Agents, Deployments, Monitoring, Cost Management và Settings.

---

## 🛠️ Yêu cầu hệ thống

Trước khi khởi chạy dự án, hãy đảm bảo máy tính của bạn đã cài đặt:
- **Node.js** (Phiên bản v18 trở lên được khuyến nghị)
- **NPM** (Đi kèm sẵn khi cài đặt Node.js)

---

## 🚀 Hướng dẫn khởi chạy nhanh

Hãy thực hiện các bước sau trong terminal để chạy dự án cục bộ:

### Bước 1: Di chuyển vào thư mục dự án
```bash
cd frontend
```

### Bước 2: Cài đặt các thư viện phụ thuộc (Dependencies)
Nếu đây là lần đầu tiên chạy dự án, hãy cài đặt các gói tài nguyên:
```bash
npm install
```

### Bước 3: Khởi chạy Máy chủ Phát triển (Development Server)
Khởi chạy dự án ở chế độ phát triển để xem trực tiếp giao diện:
```bash
npm run dev
```
Sau khi chạy lệnh này thành công, terminal sẽ hiển thị địa chỉ cục bộ của máy chủ (thường là **http://localhost:5173**). Hãy mở trình duyệt và truy cập địa chỉ này để trải nghiệm dashboard.

### Bước 4: Đóng gói Sản phẩm (Production Build)
Để xác minh tính đúng đắn của mã nguồn hoặc đóng gói tối ưu để triển khai thực tế:
```bash
npm run build
```
Sản phẩm đóng gói tĩnh sẽ được tạo ra trong thư mục `dist/` chỉ trong vài chục mili-giây.

---

## 📁 Cấu trúc Thư mục Mới (Modular Architecture)

Dự án đã được tái cấu trúc triệt để tách biệt rõ ràng giữa Layout hiển thị (HTML), xử lý logic (JS) và phong cách định dạng (CSS):

```text
unified-ai-software-dashboard/
├── index.html                  # Khung ứng dụng (App Shell) chứa Sidebar, Header và cổng Viewport rỗng
├── vite.config.js              # Cấu hình máy chủ Vite và Reverse Proxy kết nối API Backend
├── package.json                # Định nghĩa các tập lệnh npm và dependencies
├── report.html                 # Báo cáo kỹ thuật chi tiết về cơ chế tích hợp API động
├── src/
│   ├── main.js                 # Điểm khởi chạy chính (Entry point), khởi tạo Router và nạp views
│   ├── js/
│   │   ├── router.js           # Bộ điều hướng client-side điều phối chuyển màn hình động
│   │   ├── api.js              # Khách hàng API tập trung hóa, tự động đính kèm Token JWT
│   │   └── views/
│   │       ├── BaseView.js     # Class cơ sở quản lý vòng đời hiển thị (Mount/Update/Unmount)
│   │       ├── OverviewView.js # Logic xử lý màn hình chính Overview Dashboard
│   │       ├── ProjectsView.js # Logic xử lý màn hình Projects & Flutter MVP builder
│   │       ├── ...             # Các lớp logic tự trị tương ứng cho từng màn hình
│   │       └── SettingsView.js
│   ├── views/                  # Nơi lưu trữ riêng tệp HTML giao diện của từng màn hình
│   │   ├── overview.html
│   │   ├── projects.html
│   │   ├── project-detail.html
│   │   ├── ...
│   │   └── settings.html
│   └── styles/                 # Thư mục stylesheet CSS riêng cho từng thành phần
│       ├── main.css
│       ├── sidebar.css
│       ├── overview.css
│       └── ...
```

---

## 🔌 Cơ chế Kết nối API Backend

Hệ thống đã thiết lập sẵn cơ chế kết nối API realtime thông suốt:

1.  **Vòng lặp realtime 5s**: Khi bạn mở bất kỳ màn hình nào (Overview, Pipelines, Costs, Monitoring, v.v.), Class View tương ứng sẽ tự động thiết lập một bộ đệm gọi API thông qua `src/js/api.js` sau mỗi 5 giây.
2.  **Tránh lỗi rò rỉ bộ nhớ**: Khi chuyển sang trang khác, bộ đếm thời gian này sẽ được gỡ bỏ hoàn toàn ở hàm `onUnmount()`, tránh việc gọi API ngầm lãng phí băng thông trình duyệt.
3.  **Tự động đính kèm JWT**: Bạn chỉ cần điền Token JWT tại tab **Pipelines** hoặc **Settings**, tệp `src/js/api.js` sẽ tự động đính kèm token này vào tiêu đề `Authorization: Bearer <token>` trên mỗi yêu cầu mạng.
4.  **Reverse Proxy**: Vite server chuyển tiếp mọi yêu cầu `/api/...` lên Backend API thực tế chạy tại cổng `http://127.0.0.1:8000` thông qua cấu hình proxy trong `vite.config.js`.

---

## 📄 Báo cáo Kỹ thuật Đính kèm
Để biết thêm thông tin chi tiết về sơ đồ luồng dữ liệu API và cơ chế hoạt động chi tiết của mã nguồn, hãy mở trực tiếp tệp [report.html](report.html) trong thư mục dự án.
