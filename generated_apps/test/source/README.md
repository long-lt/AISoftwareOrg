# Test

Generated Flutter MVP source.

## Run

```bash
flutter pub get
flutter run
```

## Run With Local Backend

```bash
flutter run --dart-define=USE_BACKEND_API=true --dart-define=API_BASE_URL=http://127.0.0.1:8001
```

## Generated Scope

- Material 3 app shell
- Bottom navigation
- Home screen
- Feature screens
- API client, environment config, and dependency injection
- DTO mappers and remote data sources for generated backend endpoints
- Shared state and card widgets
- Theme generated from UI/UX phase
- Widget and logic smoke tests under `test/`
