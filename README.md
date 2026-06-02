# Unified AI Software Factory

**Unified AI Software Factory (`unified-ai-software-org`)** là một nền tảng nhà máy phần mềm tự động hóa toàn phần (Software Factory) thế hệ mới. Dự án được thiết lập bằng cách hợp nhất hai hệ thống AI Agent tiên tiến:
1. **AISoftwareOrg**: Khung điều phối đa tác nhân (Multi-Agent System) mô phỏng một tổ chức phần mềm thực tế với các vị trí chuyên trách (PM, Dev, QA, Git, DevOps) hoạt động bất đồng bộ trên lõi điều phối `LangGraph`.
2. **flutter_ai_factory**: Quy trình khép kín chuyên sâu 12 bước (12-Phase Pipeline) tự động sinh mã nguồn ứng dụng di động Flutter và API Backend từ mô tả ngôn ngữ tự nhiên, tự sửa lỗi Dart qua phân tích QA tĩnh và smoke test.

Hệ thống cung cấp một bảng quản trị độc lập (SaaS Dashboard) tinh xảo được tích hợp trực tiếp, giao tiếp qua REST APIs thời gian thực để giám sát chi tiết hiệu năng, chi phí tokens và lịch sử hoạt động của các bots.

---

## 📚 Tài liệu kỹ thuật dự án (System Documentation)

Hệ thống cung cấp bộ tài liệu kỹ thuật, kế hoạch phát triển và phân tích kiến trúc chi tiết đặt tại thư mục `docs/`. Bạn có thể truy cập nhanh qua các liên kết dưới đây:

*   **[CLAUDE.md (Developer Guide)](file:///Users/long/Desktop/AI_/AISoftwareOrg/docs/CLAUDE.md)** hoặc bản sao tại gốc **[CLAUDE.md](file:///Users/long/Desktop/AI_/AISoftwareOrg/CLAUDE.md)**: Hướng dẫn phát triển, thiết lập môi trường ảo, các lệnh vận hành Backend/Frontend, và suite kiểm thử tự động.
*   **[Báo cáo tổng quan dự án (Project Review Dashboard)](file:///Users/long/Desktop/AI_/AISoftwareOrg/docs/project_review.html)**: Bảng giao diện HTML đánh giá chi tiết mức độ hoàn thiện, danh sách AI agents chuyên trách, và chất lượng mã nguồn.
*   **[Kế hoạch triển khai dự án (Project Plan - Markdown)](file:///Users/long/Desktop/AI_/AISoftwareOrg/docs/project_plane.md)**: Phân tích lộ trình phát triển 4 giai đoạn, quản trị rủi ro kỹ thuật và thiết kế hệ thống.
*   **[Kế hoạch triển khai dự án tương tác (Project Plan - Interactive Dashboard)](file:///Users/long/Desktop/AI_/AISoftwareOrg/docs/project_plane.html)**: Bản kế hoạch HTML tương tác với timeline động và bộ ước tính chi phí API LLM giả lập.
*   **[Bản đồ cải tiến kiến trúc (Improvement Roadmap)](file:///Users/long/Desktop/AI_/AISoftwareOrg/docs/improvement_roadmap.html)**: Dashboard theo dõi và lọc danh sách cải tiến kỹ thuật (P0, P1, P2) cho hệ thống, backend, và agents.
*   **[Tổng quan kiến trúc hệ thống (Architecture Overview)](file:///Users/long/Desktop/AI_/AISoftwareOrg/docs/architecture_overview.html)**: Phân tích luồng dữ liệu điều phối LangGraph bằng sơ đồ vector, ma trận phân quyền bảo mật (RBAC), và chi tiết 12 bước Flutter pipeline.
*   **[Nhật ký thay đổi (Changelog)](file:///Users/long/Desktop/AI_/AISoftwareOrg/docs/changelog.md)**: Theo dõi tiến trình cập nhật tính năng, sửa lỗi và nâng cấp phiên bản hệ thống qua các mốc v1.0.0, v1.1.0, v1.2.0.
*   **[Hướng dẫn vận hành cho Quản trị viên (Operator & Admin Manual)](file:///Users/long/Desktop/AI_/AISoftwareOrg/docs/admin_manual.html)**: Cẩm nang hướng dẫn sử dụng Dashboard, quản lý hàng đợi tri thức HITL Queue, phê duyệt các Checkpoints nhạy cảm và đổi mô hình LLM.

---

## 📁 Cấu trúc thư mục dự án

Mã nguồn được tổ chức phân lớp rõ ràng, phân tách rạch ròi giữa phân hệ API Server (Backend) và phân hệ Giao diện SPA (Frontend):

```
unified-ai-software-org/
├── dashboard/               # [Backend] FastAPI API Server (app.py, jwt_utils.py)
├── frontend/                # [Frontend] Giao diện SPA viết bằng Vite & Vanilla JS
│   ├── src/                 # Mã nguồn JS, Router, Styles, Views của Dashboard
│   ├── public/              # File tĩnh của Frontend
│   ├── dist/                # Bản phân phối production sau khi biên dịch
│   └── package.json         # Quản lý script và dependencies của Frontend
├── agents/                  # [Core] Định nghĩa các tác nhân AI của 2 nhóm chuyên trách
│   ├── software_org/        # Bots quản trị: pm_agent, planner_agent, qa_agent, git_agent...
│   └── flutter_factory/     # Bots chế tạo: ba_agent, architect_agent, dev_agent, security_agent...
├── config/                  # Thiết lập cấu hình hệ thống, env và LLM Providers Registry
├── core/                    # Lõi vận hành: logging tập trung, cost tracker, registry providers
├── memory/ & storage/       # Lưu trữ tri thức agent tự học, checkpoints và cấu hình SQLite
├── system/                  # Human-in-the-loop: Hàng đợi duyệt kinh nghiệm và checkpoints
├── workflows/               # Định nghĩa kịch bản luồng công việc (Flutter MVP pipeline 12 bước)
├── workspace/               # Phân vùng làm việc cô lập chứa code và specs của các app di động được sinh ra
├── requirements.txt         # Quản lý dependencies Python của Backend
└── docker-compose.yml       # Khởi động dịch vụ hàng đợi Redis nhanh
```

---

## ⚡ Các tính năng cốt lõi

- **Luồng sinh ứng dụng di động 12 bước (12-Phase Pipeline)**: Quy trình khép kín đi từ specs nghiệp vụ (`BA`) &rarr; Thiết kế cấu trúc dữ liệu và API (`Backend`) &rarr; Thiết kế kiến trúc (`Architect`) &rarr; Thiết kế giao diện (`UI/UX`) &rarr; Lập trình code Dart (`Dev`) &rarr; Phân tích lỗi QA tĩnh &rarr; Tự sửa code (`Refactor/Repair Loop`) &rarr; Xác minh khởi chạy (`Runtime`) &rarr; Quét bảo mật &rarr; Phê duyệt (`Reviewer`) &rarr; Đóng gói nén mã nguồn (`Export`).
- **Vòng lặp sửa lỗi tự động (Repair Loop)**: QA Agent thực hiện phân tích tĩnh mã nguồn bằng lệnh `flutter analyze`. Nếu phát hiện lỗi Dart (status FAIL), danh sách bug (`bug_list.md`) sẽ được chuyển tới Refactor Agent để tự động viết đè sửa code. Vòng lặp này thực hiện liên tục cho đến khi đạt chỉ số PASS biên dịch hoặc vượt mức `max_repair_attempts`.
- **Hệ thống tự học & Checkpoints (Human-in-the-Loop)**: Hỗ trợ các chốt chặn phê duyệt mã nguồn của tác nhân và hàng đợi `ApprovalQueue` để Quản trị viên duyệt/từ chối các tri thức, kinh nghiệm chạy task mà Agent tự đúc rút.
- **Phân quyền tác nhân (RBAC)**: Giới hạn nghiêm ngặt quyền đọc/ghi file hệ thống của từng agent (quyền `READ`, `WRITE`, `EXECUTE`, `CRITICAL`), ghi nhận nhật ký vi phạm bảo mật thời gian thực.
- **Giám sát chi phí API Tokens thật**: Ghi nhận chi tiết số tiền mặt USD thật và tokens tiêu tốn của mỗi lần Agent gọi mô hình LLM, thống kê biểu đồ donut phân bổ chi phí trực tiếp trên Dashboard.

---

## 🚀 Hướng dẫn khởi chạy hệ thống

### 1. Chuẩn bị môi trường
- Hệ điều hành hỗ trợ: macOS, Linux, Windows.
- Yêu cầu cài đặt sẵn: **Python 3.10+**, **Node.js 18+**, **Docker/Redis**.

### 2. Thiết lập biến môi trường
Sao chép file `.env.example` thành `.env` tại thư mục gốc và điền các khóa API tương ứng:
```bash
cp .env.example .env
```
Các cấu hình quan trọng trong `.env`:
- `LLM_PROVIDER`: mặc định chọn `openrouter` (OpenRouter) để tối ưu chi phí, hoặc `openai`, `gemini`.
- `LLM_API_KEY`: API Key tương ứng với nhà cung cấp.
- `JOB_QUEUE_BACKEND`: thiết lập `thread` (chạy nền bất đồng bộ qua Python Threading) hoặc `rq` (hàng đợi Redis chuyên nghiệp).
- `REDIS_URL`: đường dẫn kết nối Redis (mặc định `redis://localhost:6379/0`).

---

### 3. Vận hành dịch vụ Backend & APIs

#### Bước A: Khởi động hàng đợi Redis (Nếu cấu hình `rq`)
```bash
docker-compose up -d
```

#### Bước B: Kích hoạt môi trường ảo và cài đặt dependencies Python
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Bước C: Khởi động API Server
```bash
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
```
Server APIs sẽ chạy tại địa chỉ: `http://localhost:8000`.
- Tài liệu tự động Swagger API Docs: [http://localhost:8000/docs](http://localhost:8000/docs).

---

### 4. Vận hành phân hệ Giao diện (Frontend UI)

Dự án hỗ trợ cả hai cơ chế vận hành giao diện linh hoạt:

#### Cách 1: Chạy song song trong môi trường Developer (Dev Mode)
Chạy hot-reload Frontend bằng máy chủ Vite:
```bash
cd frontend
npm install   # Cài đặt thư viện nếu chưa có
npm run dev
```
Giao diện Developer hoạt động tại: `http://localhost:5173`.
*Lưu ý: Mọi yêu cầu `/api` gửi tới cổng 5173 sẽ được tự động chuyển tiếp (proxy) về cổng 8000 của Backend.*

#### Cách 2: Tích hợp đóng gói sản xuất (Production Mode - Khuyên dùng)
Biên dịch đóng gói toàn bộ Frontend sang HTML/JS tĩnh để Backend FastAPI tự phục vụ trực tiếp trên cùng một cổng `8000`:
```bash
cd frontend
npm run build
```
Sau khi chạy build xong, bạn chỉ cần khởi động server Backend FastAPI và truy cập thẳng địa chỉ: `http://localhost:8000`. Giao diện Dashboard sẽ được nạp và hoạt động trực tiếp từ đây.

---

## 🛠️ Danh sách REST APIs chính (dashboard/app.py)

Hệ thống Backend cung cấp bộ REST APIs đầy đủ để tương tác:

- **Giám sát hoạt động**:
  - `GET /api/tasks`: Lấy tỷ lệ thành công của các pipeline, tail logs nhiệm vụ.
  - `GET /api/agents`: Stream logs Tail hoạt động chi tiết thời gian thực của từng bot.
  - `GET /api/permissions`: Xem nhật ký vi phạm phân quyền RBAC của các Agent.
  - `GET /api/costs`: Tổng hợp chi phí tokens USD theo agent và theo task.
- **Dynamic Models & Providers Registry**:
  - `GET /api/providers`: Lấy danh sách LLM Providers đang kích hoạt trong hệ thống.
  - `POST /api/providers/{name}/use`: Kích hoạt đổi Provider LLM chủ động trực tiếp.
  - `GET /api/models`: Lấy danh sách các models đang sẵn sàng từ API của Provider active.
- **Human-in-the-Loop Gateways**:
  - `GET /api/experiences`: Danh sách tri thức Agent tự đúc rút chờ phê duyệt.
  - `POST /api/experiences/{id}/approve`: Duyệt nạp tri thức đó vào cơ sở dữ liệu chung.
  - `GET /api/checkpoints`: Danh sách checkpoint tác vụ nhạy cảm đang bị tạm dừng chờ quản trị viên nhấn duyệt.
- **Job Generation Engine**:
  - `GET /api/jobs`: Danh sách ứng dụng di động đang được chế tạo hoặc đã thành công.
  - `POST /api/jobs`: Điền mô tả, tính năng để gửi yêu cầu sinh app vào hàng đợi.
  - `GET /api/jobs/{slug}/phases`: Trạng thái chi tiết của 12 phase cho một ứng dụng cụ thể.
  - `GET /api/jobs/{slug}/download`: Tải gói mã nguồn zip nén hoàn chỉnh của ứng dụng.

---

## 📄 Bản quyền & Đóng góp
Dự án được xây dựng và phát triển dưới dạng mã nguồn mở phục vụ cho các nghiên cứu về Hệ thống đa tác nhân (Multi-Agent Systems) tự trị biên dịch mã nguồn di động phức tạp.
