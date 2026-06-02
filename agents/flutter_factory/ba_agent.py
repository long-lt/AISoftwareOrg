from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BADocuments:
    requirements: str
    user_stories: str
    feature_list: str
    acceptance_criteria: str
    product_spec: str
    data_model: str
    user_flows: str
    acceptance_tests: str
    non_functional_requirements: str


def _list_items(items: list[str], fallback: str = "Chưa khai báo") -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def _feature_title(feature: str) -> str:
    return feature.strip().capitalize()


def _infer_modules(features: list[str]) -> list[str]:
    base_modules = ["Onboarding", "Home", "Navigation", "Settings"]
    feature_modules = [_feature_title(feature) for feature in features]
    return feature_modules + [module for module in base_modules if module not in feature_modules]


def _feature_entity_name(feature: str) -> str:
    words = [part for part in feature.strip().replace("-", "_").split("_") if part]
    return "".join(part.capitalize() for part in words) or "CoreItem"


def _feature_fields(feature: str) -> list[dict[str, str | bool]]:
    base_fields: list[dict[str, str | bool]] = [
        {"name": "id", "type": "string", "required": True},
        {"name": "title", "type": "string", "required": True},
        {"name": "description", "type": "string", "required": False},
        {"name": "created_at", "type": "datetime", "required": False},
        {"name": "updated_at", "type": "datetime", "required": False},
    ]
    extra_fields: dict[str, list[dict[str, str | bool]]] = {
        "product": [
            {"name": "price", "type": "decimal", "required": True},
            {"name": "inventory_count", "type": "integer", "required": True},
            {"name": "image_url", "type": "string", "required": False},
        ],
        "cart": [
            {"name": "quantity", "type": "integer", "required": True},
            {"name": "subtotal", "type": "decimal", "required": True},
        ],
        "checkout": [
            {"name": "payment_status", "type": "string", "required": True},
            {"name": "shipping_address", "type": "string", "required": True},
        ],
        "profile": [
            {"name": "email", "type": "string", "required": True},
            {"name": "display_name", "type": "string", "required": True},
        ],
        "notification": [
            {"name": "read", "type": "boolean", "required": True},
            {"name": "sent_at", "type": "datetime", "required": True},
        ],
        "favorite": [
            {"name": "target_id", "type": "string", "required": True},
            {"name": "target_type", "type": "string", "required": True},
        ],
        "playlist": [
            {"name": "track_count", "type": "integer", "required": True},
            {"name": "cover_url", "type": "string", "required": False},
        ],
        "player": [
            {"name": "track_url", "type": "string", "required": True},
            {"name": "duration_seconds", "type": "integer", "required": True},
        ],
        "chat": [
            {"name": "last_message", "type": "string", "required": False},
            {"name": "unread_count", "type": "integer", "required": True},
        ],
        "message": [
            {"name": "sender_id", "type": "string", "required": True},
            {"name": "body", "type": "string", "required": True},
        ],
        "todo": [
            {"name": "completed", "type": "boolean", "required": True},
            {"name": "due_date", "type": "datetime", "required": False},
        ],
        "task": [
            {"name": "completed", "type": "boolean", "required": True},
            {"name": "due_date", "type": "datetime", "required": False},
        ],
    }
    return [*base_fields, *extra_fields.get(feature, [])]


def _feature_actions(feature: str) -> list[str]:
    action_map = {
        "product": ["list_products", "view_product_detail", "filter_products"],
        "search": ["submit_query", "view_results", "clear_query"],
        "cart": ["add_to_cart", "update_quantity", "remove_from_cart"],
        "checkout": ["review_order", "submit_order", "handle_payment_result"],
        "profile": ["view_profile", "update_profile"],
        "notification": ["list_notifications", "mark_notification_read"],
        "favorite": ["toggle_favorite", "list_favorites"],
        "playlist": ["list_playlists", "view_playlist", "reorder_tracks"],
        "player": ["play", "pause", "seek", "skip_next"],
        "chat": ["list_conversations", "open_conversation"],
        "message": ["send_message", "receive_message"],
        "todo": ["create_task", "update_task", "complete_task", "filter_tasks"],
        "task": ["create_task", "update_task", "complete_task", "filter_tasks"],
    }
    return action_map.get(feature, [f"list_{feature}", f"view_{feature}", f"update_{feature}"])


def _build_product_spec(app_input: dict[str, Any], modules: list[str]) -> dict[str, Any]:
    name = app_input["name"]
    features = app_input.get("features", []) or ["core"]
    target_level = app_input.get("target", "mvp_demo")
    feature_specs = []
    for index, feature in enumerate(features, start=1):
        title = _feature_title(feature)
        feature_specs.append(
            {
                "id": f"F{index:02d}",
                "key": feature,
                "name": title,
                "priority": "must_have" if index <= 5 else "should_have",
                "module": title,
                "description": f"Cho phép người dùng sử dụng luồng {title}.",
                "roles": ["guest", "customer"] if feature in {"product", "search"} else ["customer"],
                "permissions": [
                    {
                        "role": "customer",
                        "actions": _feature_actions(feature),
                    }
                ],
                "acceptance_criteria": [
                    f"Given người dùng mở {title}, when dữ liệu tải thành công, then danh sách hoặc nội dung {title} hiển thị đúng.",
                    f"Given {title} không có dữ liệu, when màn hình tải xong, then empty state rõ ràng được hiển thị.",
                    f"Given có lỗi khi tải {title}, when request thất bại, then error state có hành động retry.",
                ],
                "edge_cases": [
                    "Dữ liệu rỗng",
                    "Lỗi network/backend",
                    "Người dùng thao tác nhiều lần liên tiếp",
                ],
            }
        )

    return {
        "schema_version": "1.0",
        "app": {
            "name": name,
            "slug": app_input.get("slug", ""),
            "description": app_input["description"],
            "target_level": target_level,
            "platforms": app_input.get("platforms", []),
            "style": app_input.get("style", "modern"),
            "backend": app_input.get("backend", "none"),
        },
        "personas": [
            {
                "id": "customer",
                "name": "Mobile customer",
                "goals": [
                    "Hoàn thành tác vụ chính nhanh",
                    "Hiểu trạng thái dữ liệu và lỗi rõ ràng",
                ],
            },
            {
                "id": "operator",
                "name": "Business operator",
                "goals": [
                    "Theo dõi luồng sản phẩm có thể mở rộng",
                    "Có dữ liệu và report đủ để bàn giao kỹ thuật",
                ],
            },
        ],
        "roles": [
            {"id": "guest", "description": "Người dùng chưa đăng nhập"},
            {"id": "customer", "description": "Người dùng chính của app"},
        ],
        "modules": modules,
        "features": feature_specs,
        "quality_gates": {
            "flutter_analyze": "pass",
            "flutter_test": "pass",
            "minimum_coverage_percent": 80,
            "runtime_build": "pass",
            "security_blockers": 0,
        },
        "open_questions": [
            "Backend/provider production cụ thể chưa được xác nhận.",
            "Authentication/payment provider chưa được xác nhận nếu app cần thương mại hóa đầy đủ.",
        ],
    }


def _build_data_model(app_input: dict[str, Any]) -> dict[str, Any]:
    features = app_input.get("features", []) or ["core"]
    entities = []
    for feature in features:
        entity_name = _feature_entity_name(feature)
        entities.append(
            {
                "name": entity_name,
                "feature": feature,
                "table_name": f"{feature}_items",
                "fields": _feature_fields(feature),
                "indexes": ["id"],
            }
        )

    relationships = []
    feature_set = set(features)
    if {"cart", "product"}.issubset(feature_set):
        relationships.append(
            {
                "from": "Cart",
                "to": "Product",
                "type": "many_to_one",
                "description": "Cart item references a product.",
            }
        )
    if {"favorite", "product"}.issubset(feature_set):
        relationships.append(
            {
                "from": "Favorite",
                "to": "Product",
                "type": "many_to_one",
                "description": "Favorite can reference a product.",
            }
        )
    if {"checkout", "cart"}.issubset(feature_set):
        relationships.append(
            {
                "from": "Checkout",
                "to": "Cart",
                "type": "one_to_many",
                "description": "Checkout reviews cart items before order submission.",
            }
        )

    return {
        "schema_version": "1.0",
        "storage": {
            "primary": "backend_database",
            "local_cache": "optional",
            "recommended_database": "postgresql_for_production_sqlite_for_local",
        },
        "entities": entities,
        "relationships": relationships,
    }


def _validate_contract(product_spec: dict[str, Any], data_model: dict[str, Any]) -> None:
    required_product_keys = {"schema_version", "app", "personas", "roles", "features", "quality_gates"}
    missing_product_keys = required_product_keys - set(product_spec)
    if missing_product_keys:
        raise ValueError(f"product_spec.json thiếu field: {sorted(missing_product_keys)}")

    if not product_spec["features"]:
        raise ValueError("product_spec.json phải có ít nhất một feature")

    for feature in product_spec["features"]:
        for key in ["id", "key", "name", "priority", "acceptance_criteria"]:
            if key not in feature:
                raise ValueError(f"Feature spec thiếu field `{key}`: {feature}")
        if not feature["acceptance_criteria"]:
            raise ValueError(f"Feature `{feature['key']}` thiếu acceptance criteria")

    if "entities" not in data_model or not data_model["entities"]:
        raise ValueError("data_model.json phải có entities")

    for entity in data_model["entities"]:
        if "name" not in entity or "fields" not in entity or not entity["fields"]:
            raise ValueError(f"Entity data model không hợp lệ: {entity}")


def generate_ba_documents(app_input: dict[str, Any]) -> BADocuments:
    name = app_input["name"]
    description = app_input["description"]
    platforms = app_input.get("platforms", [])
    style = app_input.get("style", "modern")
    backend = app_input.get("backend", "none")
    features = app_input.get("features", [])
    modules = _infer_modules(features)
    product_spec_data = _build_product_spec(app_input, modules)
    data_model_data = _build_data_model(app_input)
    _validate_contract(product_spec_data, data_model_data)

    requirements = f"""# Requirements: {name}

## Tổng Quan

{description}

## Phạm Vi MVP

MVP tập trung vào các tính năng cốt lõi đã khai báo, chạy ổn định trên {", ".join(platforms)} và có cấu trúc đủ rõ để các phase Architect, DEV, QA tiếp tục xử lý.

## Nền Tảng

{_list_items(platforms)}

## Style UI

- {style}

## Backend

- {backend}

## Module Chính

{_list_items(modules)}

## Yêu Cầu Chức Năng

{_list_items([f"Người dùng có thể sử dụng tính năng {_feature_title(feature)}." for feature in features])}

## Yêu Cầu Phi Chức Năng

- App cần có cấu trúc dễ mở rộng cho mobile Flutter.
- UI cần nhất quán với style đã chọn.
- Luồng chính không được có trạng thái rỗng gây lỗi.
- Các lỗi network/backend cần có thông báo rõ ràng nếu backend được dùng.
- Source code cần sẵn sàng cho QA/Test Agent kiểm tra compile và logic.
"""

    story_blocks = []
    for feature in features:
        title = _feature_title(feature)
        story_blocks.append(
            f"""### {title}

**User story:** Là người dùng, tôi muốn dùng {feature} để hoàn thành nhu cầu chính trong app.

**Business value:** Tính năng này tạo giá trị trực tiếp cho trải nghiệm cốt lõi của {name}.
"""
        )

    if not story_blocks:
        story_blocks.append(
            """### Core Flow

**User story:** Là người dùng, tôi muốn mở app và hoàn thành tác vụ chính một cách rõ ràng.

**Business value:** App có một luồng MVP đủ dùng để kiểm thử và mở rộng.
"""
        )

    user_stories = f"""# User Stories: {name}

## Persona Chính

- Người dùng mobile cần trải nghiệm nhanh, rõ ràng và ổn định.

## Stories

{"\n".join(story_blocks)}
"""

    feature_rows = []
    for index, feature in enumerate(features, start=1):
        feature_rows.append(
            f"| F{index:02d} | {_feature_title(feature)} | Core | Cần có trong MVP |"
        )
    feature_table = "\n".join(feature_rows) or "| F01 | Core Flow | Core | Cần có trong MVP |"

    feature_list = f"""# Feature List: {name}

| ID | Feature | Priority | Ghi chú |
| --- | --- | --- | --- |
{feature_table}

## Module Mapping

{_list_items([f"{module}: xử lý một phần luồng sản phẩm." for module in modules])}
"""

    criteria_blocks = []
    for feature in features:
        title = _feature_title(feature)
        criteria_blocks.append(
            f"""### {title}

- Given người dùng mở app, when truy cập {feature}, then màn hình hoặc chức năng tương ứng hiển thị đúng.
- Given dữ liệu rỗng hoặc lỗi, when {feature} được tải, then app hiển thị empty/error state rõ ràng.
- Given thao tác hợp lệ, when người dùng hoàn tất hành động trong {feature}, then trạng thái UI được cập nhật đúng.
"""
        )

    if not criteria_blocks:
        criteria_blocks.append(
            """### Core Flow

- Given người dùng mở app, when vào màn hình chính, then nội dung MVP hiển thị đúng.
- Given có lỗi xảy ra, when app xử lý lỗi, then thông báo rõ ràng được hiển thị.
"""
        )

    acceptance_criteria = f"""# Acceptance Criteria: {name}

## Tiêu Chí Chung

- App build được trên target platform đã chọn.
- Navigation chính hoạt động không lỗi.
- UI tuân thủ style `{style}`.
- Không có lỗi null-safety trong flow MVP.

## Tiêu Chí Theo Tính Năng

{"\n".join(criteria_blocks)}
"""

    flow_blocks = []
    for feature in features or ["core"]:
        title = _feature_title(feature)
        flow_blocks.append(
            f"""### {title} Flow

1. Customer mở app và vào module {title}.
2. App tải dữ liệu {title} từ repository/data source.
3. Customer xem danh sách hoặc nội dung chi tiết.
4. Customer thực hiện hành động chính: {", ".join(_feature_actions(feature))}.
5. App cập nhật UI state hoặc hiển thị lỗi rõ ràng nếu thao tác thất bại.
"""
        )

    user_flows = f"""# User Flows: {name}

## Primary Persona

- Customer: người dùng chính cần hoàn thành tác vụ nhanh trên mobile.

## Flows

{"\n".join(flow_blocks)}
"""

    test_blocks = []
    for feature in features or ["core"]:
        title = _feature_title(feature)
        test_blocks.append(
            f"""### {title}

- [ ] Load success: màn hình {title} hiển thị dữ liệu chính.
- [ ] Empty state: màn hình {title} hiển thị empty state khi không có dữ liệu.
- [ ] Error state: màn hình {title} hiển thị retry khi data source lỗi.
- [ ] Main action: thao tác chính của {title} cập nhật trạng thái UI đúng.
"""
        )

    acceptance_tests = f"""# Acceptance Tests: {name}

Các test này là contract để QA/DEV Agent sinh test tự động ở các phase sau.

## Test Cases

{"\n".join(test_blocks)}
"""

    non_functional_requirements = f"""# Non-Functional Requirements: {name}

## Security

- Không hardcode secrets, token hoặc API key trong source.
- Tất cả input từ user/backend cần được validate trước khi xử lý.
- Error message không được lộ PII hoặc internal stack trace trong UI production.

## Performance

- Màn hình chính nên có first useful render dưới 2 giây trên thiết bị phổ thông.
- Các list dài cần có pagination, lazy loading hoặc virtualization ở phase production.
- Network call cần timeout và retry policy rõ ràng.

## Reliability

- App phải có loading, empty, success và failure state cho từng feature.
- Runtime build phải PASS trước khi export production/staging.
- Nếu backend không sẵn sàng, app phải hiển thị lỗi có thể retry.

## Offline And Cache

- Local cache là optional ở MVP nhưng cần contract rõ nếu target là staging/production.
- Dữ liệu cache không được dùng thay thế server truth cho checkout/payment/auth.

## Analytics And Logging

- Ghi nhận event cho screen_view, primary_action và error_state ở production target.
- Không log token, payment info, email đầy đủ hoặc PII nhạy cảm.
"""

    return BADocuments(
        requirements=requirements,
        user_stories=user_stories,
        feature_list=feature_list,
        acceptance_criteria=acceptance_criteria,
        product_spec=json.dumps(product_spec_data, ensure_ascii=False, indent=2) + "\n",
        data_model=json.dumps(data_model_data, ensure_ascii=False, indent=2) + "\n",
        user_flows=user_flows,
        acceptance_tests=acceptance_tests,
        non_functional_requirements=non_functional_requirements,
    )


def write_ba_documents(app_input: dict[str, Any], docs_dir: Path) -> list[Path]:
    documents = generate_ba_documents(app_input)
    output_files = {
        "requirements.md": documents.requirements,
        "user_stories.md": documents.user_stories,
        "feature_list.md": documents.feature_list,
        "acceptance_criteria.md": documents.acceptance_criteria,
        "product_spec.json": documents.product_spec,
        "data_model.json": documents.data_model,
        "user_flows.md": documents.user_flows,
        "acceptance_tests.md": documents.acceptance_tests,
        "non_functional_requirements.md": documents.non_functional_requirements,
    }

    written_paths: list[Path] = []
    for filename, content in output_files.items():
        path = docs_dir / filename
        path.write_text(content, encoding="utf-8")
        written_paths.append(path)

    return written_paths
