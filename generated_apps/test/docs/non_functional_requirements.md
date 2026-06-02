# Non-Functional Requirements: Test

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
