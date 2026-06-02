# Frontend Integration Report: Test

## Status

- Phase: J - Flutter API Integration
- Source: `/Users/long/Desktop/AI_/AISoftwareOrg/generated_apps/test/source`
- Product spec schema: `1.0`
- OpenAPI contract: FOUND at `/Users/long/Desktop/AI_/AISoftwareOrg/generated_apps/test/docs/openapi.yaml`

## Backend Contract Used

- `GET /api/todo`
- `GET /api/dashboard`
- `GET /api/settings`

## Generated Frontend Integration

- `source/lib/core/api/api_client.dart`
- `source/lib/core/config/app_config.dart`
- `source/lib/core/di/app_dependencies.dart`
- `source/.env.example`
- `source/lib/features/todo/data/dtos/todo_dto.dart`
- `source/lib/features/dashboard/data/dtos/dashboard_dto.dart`
- `source/lib/features/settings/data/dtos/settings_dto.dart`
- `source/lib/features/todo/data/datasources/todo_remote_data_source.dart`
- `source/lib/features/dashboard/data/datasources/dashboard_remote_data_source.dart`
- `source/lib/features/settings/data/datasources/settings_remote_data_source.dart`

## Runtime Configuration

- `API_BASE_URL`: backend base URL.
- `APP_ENV`: local/staging/production marker.
- `USE_BACKEND_API`: set `true` to call generated FastAPI endpoints.

## Verification Intent

- Widget tests can run without a backend by using generated seed fallback.
- API client contract tests use an injected fake HTTP client.
- Production/staging runs should pass `--dart-define=USE_BACKEND_API=true`.
