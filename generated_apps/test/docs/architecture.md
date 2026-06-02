# Architecture: Test

## Mục Tiêu Kiến Trúc

Thiết kế app Flutter theo hướng Clean Architecture, feature-first và đủ rõ để DEV Agent sinh source code có thể build, test và mở rộng.

## Bối Cảnh Sản Phẩm

x

## Target Platform

- Chưa khai báo

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

- Todo
- Dashboard
- Settings

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
