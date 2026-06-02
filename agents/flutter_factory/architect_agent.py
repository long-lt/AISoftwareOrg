from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArchitectDocuments:
    architecture: str
    folder_structure: str
    state_management: str
    api_strategy: str
    database_strategy: str


def _feature_name(feature: str) -> str:
    return feature.strip().lower().replace(" ", "_")


def _title(value: str) -> str:
    return value.strip().replace("_", " ").title()


def _list_items(items: list[str], fallback: str = "Chưa khai báo") -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def _feature_modules(features: list[str]) -> list[str]:
    if not features:
        return ["home"]
    return [_feature_name(feature) for feature in features]


def generate_architect_documents(app_input: dict[str, Any]) -> ArchitectDocuments:
    name = app_input["name"]
    description = app_input["description"]
    platforms = app_input.get("platforms", [])
    backend = app_input.get("backend", "none")
    features = app_input.get("features", [])
    modules = _feature_modules(features)
    module_list = _list_items([_title(module) for module in modules])

    architecture = f"""# Architecture: {name}

## Mục Tiêu Kiến Trúc

Thiết kế app Flutter theo hướng Clean Architecture, feature-first và đủ rõ để DEV Agent sinh source code có thể build, test và mở rộng.

## Bối Cảnh Sản Phẩm

{description}

## Target Platform

{_list_items(platforms)}

## Architecture Style

- Clean Architecture
- Feature-first folder structure
- Dependency inversion giữa `presentation`, `domain`, `data`
- Tách rõ UI, state, business logic và data access

## Layer Chính

- `presentation`: screen, widget, cubit/bloc, view state
- `domain`: entity, repository contract, use case
- `data`: model DTO, data source, repository implementation
- `core`: routing, theme, network, error handling, constants

## Feature Modules

{module_list}

## Package Khuyến Nghị

- `go_router` cho navigation
- `flutter_bloc` hoặc `riverpod` cho state management
- `dio` cho REST API
- `freezed` và `json_serializable` cho immutable model nếu app có API phức tạp
- `hive` hoặc `isar` cho local cache đơn giản

## Quy Ước Lỗi

- Data layer trả lỗi đã chuẩn hóa.
- Domain layer không phụ thuộc trực tiếp vào Dio hoặc local database.
- Presentation layer hiển thị loading, empty, error và success state rõ ràng.
"""

    feature_tree = "\n".join(
        f"""│   ├── {module}/
│   │   ├── data/
│   │   │   ├── datasources/
│   │   │   ├── models/
│   │   │   └── repositories/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── repositories/
│   │   │   └── usecases/
│   │   └── presentation/
│   │       ├── cubit/
│   │       ├── screens/
│   │       └── widgets/"""
        for module in modules
    )

    folder_structure = f"""# Folder Structure: {name}

```text
lib/
├── main.dart
├── app.dart
├── core/
│   ├── config/
│   ├── constants/
│   ├── errors/
│   ├── network/
│   ├── router/
│   ├── theme/
│   └── utils/
├── features/
{feature_tree}
└── shared/
    ├── widgets/
    └── extensions/
```

## Nguyên Tắc

- Mỗi feature tự sở hữu data, domain và presentation.
- `core/` chỉ chứa hạ tầng dùng chung.
- `shared/` chỉ chứa UI/helper thật sự dùng lại nhiều nơi.
- Không import ngược từ feature này sang feature khác nếu chưa có contract rõ ràng.
"""

    cubit_lines = "\n".join(
        f"- `{module.capitalize()}Cubit`: quản lý state cho feature {_title(module)}."
        for module in modules
    )

    state_management = f"""# State Management: {name}

## Lựa Chọn Đề Xuất

Sử dụng `flutter_bloc` với Cubit cho MVP.

## Lý Do

- Cubit đủ nhẹ cho MVP.
- Dễ test logic presentation.
- Phù hợp với Clean Architecture và feature-first.
- DEV Agent có thể generate code theo pattern thống nhất.

## Cubit Dự Kiến

{cubit_lines}

## State Chuẩn

Mỗi feature nên có các state tối thiểu:

- `initial`
- `loading`
- `empty`
- `success`
- `failure`

## Quy Ước

- Cubit chỉ gọi use case.
- Use case trả dữ liệu domain hoặc lỗi domain.
- Widget không gọi trực tiếp repository/data source.
"""

    has_backend = str(backend).strip().lower() not in {"", "none", "no", "không"}
    if has_backend:
        api_detail = f"""## Backend Được Khai Báo

- {backend}

## Chiến Lược API

- Sử dụng `dio` làm HTTP client.
- Tạo `ApiClient` dùng chung trong `core/network`.
- Mỗi feature có remote data source riêng.
- DTO nằm trong `features/<feature>/data/models`.
- Repository implementation map DTO sang entity domain.

## Error Handling

- Timeout, unauthorized, server error và parse error phải được map thành lỗi domain.
- Presentation layer chỉ nhận message đã chuẩn hóa.
"""
    else:
        api_detail = """## Backend Được Khai Báo

- Chưa có backend.

## Chiến Lược API

- Chưa cần tích hợp API trong MVP.
- Vẫn chuẩn bị `core/network` rỗng hoặc tối thiểu để dễ mở rộng.
- Data source có thể dùng mock/local data trước.
"""

    api_strategy = f"""# API Strategy: {name}

{api_detail}

## Contract Gợi Ý

- Repository contract nằm trong domain layer.
- Data source interface nằm trong data layer.
- Không để UI phụ thuộc vào DTO hoặc response raw.
"""

    database_strategy = f"""# Database Strategy: {name}

## Lựa Chọn Cho MVP

Sử dụng local storage nhẹ, ưu tiên `hive` cho cache đơn giản và dữ liệu key-value.

## Khi Nào Dùng Database Mạnh Hơn

- Dùng `isar` nếu cần query local phức tạp.
- Dùng `drift` nếu cần schema quan hệ, migration rõ ràng hoặc query SQL.

## Dữ Liệu Có Thể Lưu Local

- User preferences
- Cache danh sách dữ liệu chính
- Trạng thái favorite/offline nếu feature yêu cầu

## Quy Ước

- Local data source nằm trong từng feature.
- Entity domain không phụ thuộc model local database.
- Repository quyết định ưu tiên remote/local theo nhu cầu feature.
"""

    return ArchitectDocuments(
        architecture=architecture,
        folder_structure=folder_structure,
        state_management=state_management,
        api_strategy=api_strategy,
        database_strategy=database_strategy,
    )


def write_architect_documents(app_input: dict[str, Any], docs_dir: Path) -> list[Path]:
    documents = generate_architect_documents(app_input)
    output_files = {
        "architecture.md": documents.architecture,
        "folder_structure.md": documents.folder_structure,
        "state_management.md": documents.state_management,
        "api_strategy.md": documents.api_strategy,
        "database_strategy.md": documents.database_strategy,
    }

    written_paths: list[Path] = []
    for filename, content in output_files.items():
        path = docs_dir / filename
        path.write_text(content, encoding="utf-8")
        written_paths.append(path)

    return written_paths
