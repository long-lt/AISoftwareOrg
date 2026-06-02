from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class UIUXDocuments:
    design: str
    screen_list: str
    theme_config: str
    component_spec: str


def _feature_key(feature: str) -> str:
    return feature.strip().lower().replace(" ", "_")


def _title(value: str) -> str:
    return value.strip().replace("_", " ").title()


def _class_name(value: str) -> str:
    return "".join(part.capitalize() for part in _feature_key(value).split("_"))


def _list_items(items: list[str], fallback: str = "Chưa khai báo") -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def _palette_for_style(style: str) -> dict[str, str]:
    lowered = style.lower()
    if "music" in lowered:
        return {
            "primary": "0xFF1DB954",
            "secondary": "0xFF121212",
            "surface": "0xFFFFFFFF",
            "background": "0xFFF7F8FA",
            "error": "0xFFE53935",
        }
    if "dark" in lowered:
        return {
            "primary": "0xFF4F8CFF",
            "secondary": "0xFF101828",
            "surface": "0xFF1F2937",
            "background": "0xFF0B1220",
            "error": "0xFFF04438",
        }
    return {
        "primary": "0xFF2563EB",
        "secondary": "0xFF0F172A",
        "surface": "0xFFFFFFFF",
        "background": "0xFFF8FAFC",
        "error": "0xFFDC2626",
    }


def generate_uiux_documents(app_input: dict[str, Any]) -> UIUXDocuments:
    name = app_input["name"]
    description = app_input["description"]
    style = app_input.get("style", "modern")
    features = app_input.get("features", [])
    palette = _palette_for_style(str(style))
    feature_names = features or ["home"]

    screen_lines = [
        "| HomeScreen | Tổng quan app, entry point chính | User mở app | Điều hướng tới feature chính |"
    ]
    for feature in feature_names:
        title = _title(feature)
        screen_lines.append(
            f"| { _class_name(feature) }Screen | Màn hình xử lý {title} | User chọn {title} | Hiển thị loading, empty, success, failure |"
        )
    screen_lines.append(
        "| SettingsScreen | Tuỳ chỉnh cơ bản và thông tin app | User mở settings | Hiển thị cấu hình và trạng thái app |"
    )

    design = f"""# Design Spec: {name}

## Định Hướng UI

{name} sử dụng style `{style}` với giao diện mobile rõ ràng, dễ scan và tối ưu cho thao tác lặp lại.

## Bối Cảnh Sản Phẩm

{description}

## Design Principles

- Ưu tiên nội dung và tác vụ chính trên màn hình đầu tiên.
- Mỗi màn hình có một primary action rõ ràng.
- Empty, loading và error state phải được thiết kế như một phần của flow.
- Navigation đơn giản, dễ quay lại và không tạo dead-end.

## Visual System

- Primary color: `#{palette["primary"][4:]}`
- Secondary color: `#{palette["secondary"][4:]}`
- Background color: `#{palette["background"][4:]}`
- Surface color: `#{palette["surface"][4:]}`
- Error color: `#{palette["error"][4:]}`

## Typography

- Title: 24sp, weight 700
- Section title: 18sp, weight 600
- Body: 14sp, weight 400
- Caption: 12sp, weight 400

## Spacing

- Base spacing: 8px
- Screen horizontal padding: 16px
- Section gap: 24px
- Component gap: 12px
- Card padding: 16px

## Navigation

- Home là entry point.
- Feature chính đi từ Home hoặc bottom navigation.
- Settings nằm ở secondary destination.
"""

    screen_list = f"""# Screen List: {name}

| Screen | Mục đích | Entry | State cần hỗ trợ |
| --- | --- | --- | --- |
{chr(10).join(screen_lines)}

## Feature Mapping

{_list_items([f"{_title(feature)} -> {_class_name(feature)}Screen" for feature in feature_names])}
"""

    theme_config = f"""import 'package:flutter/material.dart';

class AppTheme {{
  static const Color primary = Color({palette["primary"]});
  static const Color secondary = Color({palette["secondary"]});
  static const Color appBackground = Color({palette["background"]});
  static const Color appSurface = Color({palette["surface"]});
  static const Color appError = Color({palette["error"]});

  static ThemeData light() {{
    final colorScheme = ColorScheme.fromSeed(
      seedColor: primary,
      primary: primary,
      secondary: secondary,
      surface: appSurface,
      error: appError,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: appBackground,
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: appBackground,
        foregroundColor: secondary,
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: appSurface,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: appSurface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }}
}}
"""

    component_spec = f"""# Component Spec: {name}

## AppScaffold

- Dùng chung cho các screen chính.
- Có optional app bar title.
- Có safe area.
- Padding mặc định 16px.

## FeatureCard

- Hiển thị title, subtitle, optional icon và action.
- Border radius 8px.
- Không dùng nested card.
- Tap area tối thiểu 48px.

## StateView

Hỗ trợ các trạng thái:

- Loading: progress indicator và text ngắn.
- Empty: icon, title, description và optional action.
- Error: message rõ ràng và retry action.
- Success: render content chính.

## PrimaryActionButton

- Dùng cho hành động chính của màn hình.
- Chiều cao tối thiểu 48px.
- Text ngắn, bắt đầu bằng động từ.

## Screen Header

- Title rõ ràng, tối đa 2 dòng.
- Subtitle optional.
- Không dùng hero typography trong panel nhỏ.

## Feature Components

{_list_items([f"{_title(feature)}View: component chính cho {_title(feature)}Screen." for feature in feature_names])}
"""

    return UIUXDocuments(
        design=design,
        screen_list=screen_list,
        theme_config=theme_config,
        component_spec=component_spec,
    )


def write_uiux_documents(app_input: dict[str, Any], docs_dir: Path) -> list[Path]:
    documents = generate_uiux_documents(app_input)
    output_files = {
        "design.md": documents.design,
        "screen_list.md": documents.screen_list,
        "theme_config.dart": documents.theme_config,
        "component_spec.md": documents.component_spec,
    }

    written_paths: list[Path] = []
    for filename, content in output_files.items():
        path = docs_dir / filename
        path.write_text(content, encoding="utf-8")
        written_paths.append(path)

    return written_paths
