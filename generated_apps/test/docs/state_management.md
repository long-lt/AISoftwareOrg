# State Management: Test

## Lựa Chọn Đề Xuất

Sử dụng `flutter_bloc` với Cubit cho MVP.

## Lý Do

- Cubit đủ nhẹ cho MVP.
- Dễ test logic presentation.
- Phù hợp với Clean Architecture và feature-first.
- DEV Agent có thể generate code theo pattern thống nhất.

## Cubit Dự Kiến

- `TodoCubit`: quản lý state cho feature Todo.
- `DashboardCubit`: quản lý state cho feature Dashboard.
- `SettingsCubit`: quản lý state cho feature Settings.

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
