# API Contract Reference

Tài liệu tham khảo tất cả REST API endpoints của hệ thống.

**Base URL**: `http://localhost:8000`
**Auth**: JWT Bearer token (lấy từ `/api/auth/token`)
**Content-Type**: `application/json`

---

## System

### `GET /health`

Liveness probe.

**Response:**
```json
{ "status": "ok", "queue_backend": "thread" }
```

### `GET /ready`

Readiness probe. Kiểm tra storage có load được không.

**Response (200):**
```json
{ "status": "ready" }
```

**Response (503):**
```json
{ "status": "not_ready", "error": "..." }
```

### `GET /api`

API root info.

**Response:**
```json
{
  "status": "online",
  "service": "Unified AI Software Factory API Backend",
  "version": "1.0.0",
  "docs_url": "/docs"
}
```

---

## Auth

### `POST /api/auth/token`

Tạo JWT authentication token. Endpoint này là admin-only và bắt buộc header `X-Admin-Key`.

**Headers:**
| Name | Type | Required | Description |
|---|---|---|---|
| `X-Admin-Key` | string | ✅ | Phải khớp `ADMIN_API_KEY` trong `.env` |

**Body:**
```json
{
  "team_id": "default",
  "role": "admin"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOi...",
  "team_id": "default",
  "role": "admin",
  "expires_in": 86400
}
```

Token payload chứa `team_id`, `role`, `iat`, `exp`.

**Errors:**
- `401` — Admin key thiếu hoặc không đúng
- `503` — `ADMIN_API_KEY` chưa được cấu hình

### `GET /api/auth/me`

Lấy thông tin user hiện tại từ JWT token.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{ "team_id": "default" }
```

**Errors:**
- `401` — Token không hợp lệ hoặc thiếu

---

## Jobs

### `GET /api/jobs`

Liệt kê tất cả generation jobs.

**Response:** Array of job objects.

### `POST /api/jobs`

Tạo Flutter generation job mới. Enqueue vào thread hoặc RQ.

**Body:**
```json
{
  "name": "My App",
  "description": "A todo list app",
  "platform": "android,ios",
  "style": "modern",
  "backend": "none",
  "features": "auth,notifications",
  "slug": "my-app"
}
```

| Field | Type | Default | Required |
|---|---|---|---|
| `name` | string | — | ✅ |
| `description` | string | — | ✅ |
| `platform` | string | `"android,ios"` | ❌ |
| `style` | string | `"modern"` | ❌ |
| `backend` | string | `"none"` | ❌ |
| `features` | string | `""` | ❌ |
| `slug` | string | auto-generated | ❌ |

**Response:** `202` with job object.

### `GET /api/jobs/{slug}`

Lấy thông tin một job.

**Response:** Job object hoặc `404`.

### `DELETE /api/jobs/{slug}`

Xóa job.

**Parameters:**
| In | Name | Type | Default | Description |
|---|---|---|---|---|
| Query | `purge` | bool | `false` | Nếu `true`, xóa luôn thư mục generated app trên disk |

### `GET /api/jobs/{slug}/phases`

Trạng thái chi tiết từng phase của job.

**Response:**
```json
{
  "create": "passed",
  "ba": "passed",
  "backend": "pending",
  "architect": "running",
  "uiux": "pending",
  "dev": "pending",
  "qa": "pending",
  "refactor": "pending",
  "repair": "pending",
  "runtime": "pending",
  "security": "pending",
  "reviewer": "pending",
  "export": "pending"
}
```

Status hợp lệ: `pending`, `running`, `passed`, `failed`, `skipped`, `cancelled`.

Phase 3 target sẽ mở rộng endpoint này thành response dạng list object có `phase`, `agent`, `started_at`, `finished_at`, `error`, và log metadata.

### `POST /api/jobs/{slug}/cancel`

Hủy job đang queued hoặc running.

**Response:**
```json
{
  "slug": "my-app",
  "status": "cancel_requested",
  "cancel_requested": true
}
```

Worker/pipeline sẽ phát hiện `cancel_requested` trước khi bắt đầu phase tiếp theo và chuyển job sang `cancelled`.

**Errors:**
- `404` — Job không tồn tại
- `409` — Job không còn ở trạng thái `queued` hoặc `running`

### `GET /api/jobs/{slug}/download`

Tải source code ZIP. Returns `FileResponse` hoặc `404`.

### `GET /api/jobs/{slug}/code/tree`

Browse file tree của generated app (chỉ `source/` và `docs/`).

**Response:**
```json
[
  { "path": "source/lib/main.dart", "name": "main.dart", "isDir": false, "size": 1234 },
  { "path": "source/lib/features", "name": "features", "isDir": true, "size": 0 }
]
```

### `GET /api/jobs/{slug}/code/file`

Đọc nội dung một file trong generated app.

**Parameters:**
| In | Name | Type | Required | Description |
|---|---|---|---|---|
| Query | `path` | string | ✅ | Relative path (chỉ `source/` và `docs/`, max 500KB) |

**Response:**
```json
{ "path": "source/lib/main.dart", "content": "import ..." }
```

---

## Projects

### `GET /api/projects`

Liệt kê tất cả project initiatives.

### `POST /api/projects`

Tạo project mới.

**Body:**
```json
{
  "name": "Flutter Todo App",
  "description": "A simple todo list application",
  "slug": "flutter-todo",
  "status": "discovery",
  "health": "healthy",
  "icon": "📱",
  "repository": "",
  "monthly_spend": 0,
  "sla": "100%",
  "build_progress": 0,
  "features": ["auth", "notifications"]
}
```

### `GET /api/projects/{slug}`

Lấy thông tin project. Returns `404` nếu không tìm thấy.

### `PUT /api/projects/{slug}`

Cập nhật project (upsert).

### `DELETE /api/projects/{slug}`

Xóa project.

---

## Agents

### `GET /api/agents/config`

Liệt kê cấu hình tất cả agents.

**Response:**
```json
[
  { "agent_id": "dev_agent", "name": "Dev Agent", "model": "gpt-4o", "system_prompt": "...", "updated_at": "..." }
]
```

### `POST /api/agents/config/{agent_id}`

Cập nhật model và system prompt của agent.

**Body:**
```json
{
  "model": "gpt-4o-mini",
  "system_prompt": "You are a senior developer..."
}
```

### `GET /api/agents/{agent_id}`

Lấy thông tin chi tiết một agent.

**Response:**
```json
{
  "agent_id": "dev_agent",
  "name": "Dev Agent",
  "type": "flutter_factory",
  "status": "active",
  "model": "gpt-4o",
  "system_prompt": "...",
  "description": "...",
  "updated_at": "2025-01-15T10:30:00"
}
```

### `PATCH /api/agents/{agent_id}`

Cập nhật agent (partial update).

**Body:**
```json
{
  "model": "gpt-4o-mini",
  "system_prompt": "Updated prompt..."
}
```

### `POST /api/agents/{agent_id}/test`

Test agent bằng cách gửi prompt thử nghiệm.

**Response:**
```json
{
  "agent_id": "dev_agent",
  "model": "gpt-4o",
  "status": "ok",
  "response": "OK"
}
```

---

## Settings

### `GET /api/settings`

Lấy tất cả system settings.

**Response:**
```json
{
  "daily_cost_limit": "5.00",
  "smart_model_fallback": "anthropic/claude-3.5-sonnet",
  "max_repair_attempts": "5"
}
```

### `POST /api/settings`

Cập nhật system settings. Persist vào SQLite và `.env`.

**Body:**
```json
{
  "daily_cost_limit": "10.00",
  "max_repair_attempts": "3"
}
```

### `POST /api/settings/wipe`

⚠️ **DESTRUCTIVE**: Xóa toàn bộ SQLite tables, generated apps, memory.json, re-seed defaults.

---

## Providers

### `GET /api/models`

Lấy danh sách models từ LLM provider.

**Parameters:**
| In | Name | Type | Description |
|---|---|---|---|
| Query | `provider` | string | Provider name (optional) |
| Query | `key` | string | API key (optional) |
| Query | `base_url` | string | Base URL (optional) |

### `GET /api/providers`

Liệt kê tất cả registered LLM providers.

### `POST /api/providers`

Thêm provider mới (name trong body).

**Body:**
```json
{
  "name": "my-provider",
  "base_url": "https://api.example.com/v1",
  "api_key_env": "EXAMPLE_API_KEY",
  "default_model": "example-model-v1",
  "enabled": true
}
```

### `POST /api/providers/{name}`

Thêm hoặc upsert custom provider (name trong URL).

**Body:**
```json
{
  "base_url": "https://api.example.com/v1",
  "api_key_env": "EXAMPLE_API_KEY",
  "default_model": "example-model-v1",
  "enabled": true
}
```

### `PATCH /api/providers/{name}`

Cập nhật một phần provider config.

### `DELETE /api/providers/{name}`

Xóa custom provider.

### `POST /api/providers/{name}/use`

Kích hoạt provider làm LLM chính (ghi `LLM_PROVIDER` vào `.env`).

### `POST /api/providers/{name}/test`

Test kết nối đến provider.

**Response:**
```json
{ "provider": "openrouter", "status": "ok", "models_count": 42 }
```

---

## HITL (Human-in-the-Loop)

> Các endpoint HITL yêu cầu `Authorization: Bearer <token>` header.

### `GET /api/experiences`

Liệt kê experiences (pending, approved, rejected) của team hiện tại.

### `POST /api/experiences/{exp_id}/approve`

Phê duyệt experience.

### `POST /api/experiences/{exp_id}/reject`

Từ chối experience.

**Parameters:**
| In | Name | Type | Description |
|---|---|---|---|
| Query | `reason` | string | Lý do từ chối (optional) |

### `GET /api/checkpoints`

Liệt kê checkpoints (pending, approved, rejected).

### `POST /api/checkpoints/{cp_id}/approve`

Phê duyệt checkpoint.

### `POST /api/checkpoints/{cp_id}/reject`

Từ chối checkpoint.

---

## HITL (Unified Queue)

### `GET /api/hitl/queue`

Unified queue: gộp experiences + checkpoints pending.

**Response:**
```json
{
  "pending": [
    { "type": "experience", "id": "exp-1", "content": "..." },
    { "type": "checkpoint", "id": "cp-1", "action": "..." }
  ],
  "counts": { "experiences": 3, "checkpoints": 1 }
}
```

### `POST /api/hitl/{item_id}/approve`

Phê duyệt item (tự động tìm trong experiences hoặc checkpoints).

### `POST /api/hitl/{item_id}/reject`

Từ chối item.

**Parameters:**
| In | Name | Type | Description |
|---|---|---|---|
| Query | `reason` | string | Lý do từ chối (optional) |

---

## Observability

### `GET /api/tasks`

Tóm tắt workflow tasks: total, success, failed counts + 20 logs gần nhất.

### `GET /api/agents`

Agent activity logs.

**Parameters:**
| In | Name | Type | Default | Description |
|---|---|---|---|---|
| Query | `limit` | int | `50` | Số log entries (1-500) |

### `GET /api/permissions`

100 log entries gần nhất có action `permission_denied`.

### `GET /api/costs`

Aggregated cost breakdown: total cost, total tokens, by task, by agent.

### `GET /api/costs/summary`

Cost summary overview.

**Response:**
```json
{
  "total_cost_usd": 12.50,
  "total_calls": 42,
  "avg_cost_per_call": 0.2976,
  "top_agent": "dev_agent"
}
```

### `GET /api/costs/by-agent`

Cost breakdown theo agent.

**Response:**
```json
[
  { "agent": "dev_agent", "cost_usd": 5.20, "calls": 15, "tokens_in": 50000, "tokens_out": 20000 },
  { "agent": "qa_agent", "cost_usd": 3.10, "calls": 10, "tokens_in": 30000, "tokens_out": 10000 }
]
```

### `GET /api/costs/by-job`

Cost breakdown theo job.

**Response:**
```json
[
  { "job_slug": "my-app", "cost_usd": 8.50, "calls": 25 },
  { "job_slug": "another-app", "cost_usd": 4.00, "calls": 17 }
]
```

### `GET /api/costs/daily`

Daily cost aggregation.

**Parameters:**
| In | Name | Type | Default | Description |
|---|---|---|---|---|
| Query | `days` | int | `7` | Số ngày (1-30) |

**Response:**
```json
[
  { "date": "2025-01-15", "cost_usd": 1.23, "calls": 42 }
]
```

### `GET /api/kpis`

Dashboard KPI summary.

---

## System Settings

### `GET /api/settings`

Lấy tất cả system settings.

### `GET /api/system/settings`

Alias cho `GET /api/settings`.

### `POST /api/settings`

Cập nhật system settings.

### `PATCH /api/system/settings`

Alias cho `POST /api/settings` (partial update semantics).

### `GET /api/system/status`

System status info.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "queue_backend": "thread",
  "db_path": "/path/to/dashboard/data/app.db",
  "db_exists": true,
  "generated_apps_dir": "/path/to/generated_apps"
}
```

**Response:**
```json
{
  "total_projects": 5,
  "status_breakdown": { "discovery": 2, "development": 2, "production": 1, "blocked": 0 },
  "success_rate": 85.0,
  "total_cost": 12.50,
  "active_models": 3,
  "active_providers": 2
}
```

---

## Error Format

Tất cả errors trả về JSON:

```json
{
  "detail": "Mô tả lỗi"
}
```

HTTP status codes:
- `200` — Success
- `201` — Created
- `202` — Accepted (async job)
- `400` — Bad request
- `401` — Unauthorized
- `404` — Not found
- `409` — Conflict
- `500` — Internal server error
- `503` — Service unavailable
