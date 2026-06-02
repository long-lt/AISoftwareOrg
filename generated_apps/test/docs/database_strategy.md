# Database Strategy: Test

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
