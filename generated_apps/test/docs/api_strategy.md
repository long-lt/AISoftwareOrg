# API Strategy: Test

## Backend Được Khai Báo

- Chưa có backend.

## Chiến Lược API

- Chưa cần tích hợp API trong MVP.
- Vẫn chuẩn bị `core/network` rỗng hoặc tối thiểu để dễ mở rộng.
- Data source có thể dùng mock/local data trước.


## Contract Gợi Ý

- Repository contract nằm trong domain layer.
- Data source interface nằm trong data layer.
- Không để UI phụ thuộc vào DTO hoặc response raw.
