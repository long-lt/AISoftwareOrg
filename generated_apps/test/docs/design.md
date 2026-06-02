# Design Spec: Test

## Định Hướng UI

Test sử dụng style `modern` với giao diện mobile rõ ràng, dễ scan và tối ưu cho thao tác lặp lại.

## Bối Cảnh Sản Phẩm

x

## Design Principles

- Ưu tiên nội dung và tác vụ chính trên màn hình đầu tiên.
- Mỗi màn hình có một primary action rõ ràng.
- Empty, loading và error state phải được thiết kế như một phần của flow.
- Navigation đơn giản, dễ quay lại và không tạo dead-end.

## Visual System

- Primary color: `#2563EB`
- Secondary color: `#0F172A`
- Background color: `#F8FAFC`
- Surface color: `#FFFFFF`
- Error color: `#DC2626`

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
