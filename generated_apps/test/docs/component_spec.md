# Component Spec: Test

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

- TodoView: component chính cho TodoScreen.
- DashboardView: component chính cho DashboardScreen.
- SettingsView: component chính cho SettingsScreen.
