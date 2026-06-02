from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GeneratedSource:
    paths: list[Path]


def _slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "flutter_app"


def _feature_key(feature: str) -> str:
    return _slug(feature)


def _title(value: str) -> str:
    return value.strip().replace("_", " ").title()


def _class_name(value: str) -> str:
    return "".join(part.capitalize() for part in _feature_key(value).split("_"))


def _feature_icon(feature: str) -> str:
    icons = {
        "playlist": "Icons.queue_music",
        "player": "Icons.play_circle_fill",
        "favorite": "Icons.favorite",
        "search": "Icons.search",
        "notification": "Icons.notifications",
        "todo": "Icons.check_circle",
        "task": "Icons.check_circle",
        "product": "Icons.shopping_bag",
        "cart": "Icons.shopping_cart",
        "checkout": "Icons.payments",
        "chat": "Icons.chat_bubble",
        "message": "Icons.chat_bubble",
        "profile": "Icons.person",
        "calendar": "Icons.calendar_month",
        "map": "Icons.map",
    }
    return icons.get(feature, "Icons.dashboard")


def _feature_subtitle(feature: str) -> str:
    subtitles = {
        "playlist": "Build and manage listening queues",
        "player": "Control playback and current track",
        "favorite": "Keep saved tracks one tap away",
        "search": "Find content quickly",
        "notification": "Review alerts and updates",
        "todo": "Track tasks and completion",
        "task": "Track tasks and completion",
        "product": "Browse product inventory",
        "cart": "Review selected items",
        "checkout": "Prepare payment flow",
        "chat": "Open recent conversations",
        "message": "Open recent conversations",
        "profile": "Manage account information",
        "calendar": "Review upcoming schedule",
        "map": "Explore location context",
    }
    return subtitles.get(feature, f"Open {_title(feature)} flow")


def _sample_items(feature: str) -> list[tuple[str, str]]:
    samples = {
        "playlist": [
            ("Morning Focus", "12 tracks curated for deep work."),
            ("Evening Drive", "A warm playlist for commuting."),
        ],
        "player": [
            ("Midnight City", "Now playing - M83, 4:03"),
            ("Next Up", "Queue preview with playback controls."),
        ],
        "favorite": [
            ("Saved Track", "Pinned to favorites for quick replay."),
            ("Favorite Mix", "Auto-generated from liked songs."),
        ],
        "search": [
            ("Recent Search", "Query history and suggested results."),
            ("Top Result", "Fast match from generated data."),
        ],
        "notification": [
            ("Release Reminder", "New content is available."),
            ("System Update", "Generated notification example."),
        ],
        "todo": [
            ("Plan MVP scope", "High priority - due today."),
            ("Review generated source", "Medium priority - in progress."),
        ],
        "task": [
            ("Plan MVP scope", "High priority - due today."),
            ("Review generated source", "Medium priority - in progress."),
        ],
        "product": [
            ("Wireless Headphones", "$129 - in stock."),
            ("Travel Speaker", "$79 - 4.8 rating."),
        ],
        "cart": [
            ("Cart subtotal", "2 items - estimated total $208."),
            ("Shipping option", "Standard delivery selected."),
        ],
        "checkout": [
            ("Payment method", "Card ending 4242."),
            ("Order review", "Confirm address and totals."),
        ],
        "chat": [
            ("Design Team", "Latest message: UI spec is ready."),
            ("Support", "Latest message: Ticket updated."),
        ],
        "message": [
            ("Design Team", "Latest message: UI spec is ready."),
            ("Support", "Latest message: Ticket updated."),
        ],
    }
    return samples.get(
        feature,
        [
            (f"{_title(feature)} item 1", f"Generated data for {_title(feature)}."),
            (f"{_title(feature)} item 2", "Replace this mock with real data later."),
        ],
    )


def _feature_header_widget(feature: str, title: str) -> str:
    if feature == "player":
        return """Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Icon(Icons.album, size: 48),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text('Now Playing'),
                        SizedBox(height: 4),
                        Text('Generated playback surface'),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: _cubit.loadItems,
                    icon: const Icon(Icons.play_arrow),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),"""
    if feature in {"todo", "task"}:
        return """FilledButton.icon(
            onPressed: _cubit.loadItems,
            icon: const Icon(Icons.add),
            label: const Text('Add task'),
          ),
          const SizedBox(height: 12),"""
    if feature in {"cart", "checkout"}:
        return """FilledButton.icon(
            onPressed: _cubit.loadItems,
            icon: const Icon(Icons.payments),
            label: const Text('Review checkout'),
          ),
          const SizedBox(height: 12),"""
    if feature in {"chat", "message"}:
        return """FilledButton.icon(
            onPressed: _cubit.loadItems,
            icon: const Icon(Icons.edit),
            label: const Text('New message'),
          ),
          const SizedBox(height: 12),"""
    return f"""Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: const [
                  Icon({_feature_icon(feature)}, size: 32),
                  SizedBox(width: 12),
                  Expanded(
                    child: Text('{title} generated workflow'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),"""


def _package_name(app_input: dict[str, Any]) -> str:
    return _slug(str(app_input.get("slug") or app_input["name"]))


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _dart_string(value: object) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("$", r"\$")
        .replace("'", r"\'")
        .replace("\n", r"\n")
    )


def _pubspec(app_input: dict[str, Any]) -> str:
    package = _package_name(app_input)
    description = str(app_input["description"]).replace("\n", " ")
    return f"""name: {package}
description: {description}
publish_to: "none"
version: 0.1.0+1

environment:
  sdk: ">=3.3.0 <4.0.0"

dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.2

dev_dependencies:
  flutter_test:
    sdk: flutter

flutter:
  uses-material-design: true
"""


def _main_dart(package: str) -> str:
    return f"""import 'package:flutter/material.dart';
import 'package:{package}/app.dart';

void main() {{
  runApp(const GeneratedApp());
}}
"""


def _env_example() -> str:
    return """API_BASE_URL=http://127.0.0.1:8001
APP_ENV=local
USE_BACKEND_API=true
"""


def _app_config_dart() -> str:
    return """class AppConfig {
  const AppConfig._();

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8001',
  );

  static const String environment = String.fromEnvironment(
    'APP_ENV',
    defaultValue: 'local',
  );

  static const bool useBackendApi = bool.fromEnvironment(
    'USE_BACKEND_API',
    defaultValue: false,
  );

  static const Duration requestTimeout = Duration(seconds: 5);
}
"""


def _api_client_dart(app_input: dict[str, Any]) -> str:
    package = _package_name(app_input)
    return f"""import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:{package}/core/config/app_config.dart';

class ApiException implements Exception {{
  const ApiException(this.message, {{this.statusCode}});

  final String message;
  final int? statusCode;

  @override
  String toString() {{
    if (statusCode == null) {{
      return 'ApiException: $message';
    }}
    return 'ApiException($statusCode): $message';
  }}
}}

class ApiClient {{
  ApiClient({{http.Client? httpClient, String? baseUrl}})
      : _httpClient = httpClient ?? http.Client(),
        _baseUrl = baseUrl ?? AppConfig.apiBaseUrl;

  final http.Client _httpClient;
  final String _baseUrl;

  Future<List<Map<String, dynamic>>> getList(String path) async {{
    final response = await _httpClient
        .get(_uri(path))
        .timeout(AppConfig.requestTimeout);
    final decoded = _decodeResponse(response);
    if (decoded is List) {{
      return decoded
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList(growable: false);
    }}
    if (decoded is Map<String, dynamic>) {{
      final value = decoded['data'] ?? decoded['items'] ?? decoded['results'];
      if (value is List) {{
        return value
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList(growable: false);
      }}
    }}
    return const <Map<String, dynamic>>[];
  }}

  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> body,
  ) async {{
    final response = await _httpClient
        .post(
          _uri(path),
          headers: const <String, String>{{'Content-Type': 'application/json'}},
          body: jsonEncode(body),
        )
        .timeout(AppConfig.requestTimeout);
    final decoded = _decodeResponse(response);
    if (decoded is Map<String, dynamic>) {{
      return decoded;
    }}
    throw const ApiException('Expected JSON object response');
  }}

  Uri _uri(String path) {{
    final normalizedBase = _baseUrl.endsWith('/')
        ? _baseUrl.substring(0, _baseUrl.length - 1)
        : _baseUrl;
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$normalizedBase$normalizedPath');
  }}

  Object? _decodeResponse(http.Response response) {{
    if (response.statusCode < 200 || response.statusCode >= 300) {{
      throw ApiException(
        response.body.isEmpty ? 'Request failed' : response.body,
        statusCode: response.statusCode,
      );
    }}
    if (response.body.trim().isEmpty) {{
      return null;
    }}
    return jsonDecode(response.body);
  }}
}}
"""


def _app_dependencies_dart(app_input: dict[str, Any]) -> str:
    package = _package_name(app_input)
    return f"""import 'package:{package}/core/api/api_client.dart';

class AppDependencies {{
  AppDependencies._();

  static final ApiClient apiClient = ApiClient();
}}
"""


def _web_index_html(app_input: dict[str, Any]) -> str:
    name = _dart_string(app_input["name"])
    description = _dart_string(app_input["description"])
    return f"""<!DOCTYPE html>
<html>
<head>
  <base href="$FLUTTER_BASE_HREF">
  <meta charset="UTF-8">
  <meta content="IE=Edge" http-equiv="X-UA-Compatible">
  <meta name="description" content="{description}">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name}</title>
</head>
<body>
  <script src="flutter_bootstrap.js" async></script>
</body>
</html>
"""


def _app_dart(app_input: dict[str, Any], feature_keys: list[str]) -> str:
    name = _dart_string(app_input["name"])
    imports = [
        "import 'package:flutter/material.dart';",
        "import 'package:%s/core/theme/app_theme.dart';" % _package_name(app_input),
        "import 'package:%s/features/home/presentation/screens/home_screen.dart';"
        % _package_name(app_input),
        "import 'package:%s/features/settings/presentation/screens/settings_screen.dart';"
        % _package_name(app_input),
    ]
    for feature in feature_keys:
        imports.append(
            "import 'package:%s/features/%s/presentation/screens/%s_screen.dart';"
            % (_package_name(app_input), feature, feature)
        )

    destination_items = [
        """NavigationDestination(
          icon: Icon(Icons.home_outlined),
          selectedIcon: Icon(Icons.home),
          label: 'Home',
        )"""
    ]
    pages = ["const HomeScreen()"]
    for feature in feature_keys:
        destination_items.append(
            f"""NavigationDestination(
          icon: Icon({_feature_icon(feature)}),
          selectedIcon: Icon({_feature_icon(feature)}),
          label: '{_dart_string(_title(feature))}',
        )"""
        )
        pages.append(f"const {_class_name(feature)}Screen()")
    destination_items.append(
        """NavigationDestination(
          icon: Icon(Icons.settings_outlined),
          selectedIcon: Icon(Icons.settings),
          label: 'Settings',
        )"""
    )
    pages.append("const SettingsScreen()")

    return f"""{chr(10).join(imports)}

class GeneratedApp extends StatelessWidget {{
  const GeneratedApp({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: '{name}',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: const AppShell(),
    );
  }}
}}

class AppShell extends StatefulWidget {{
  const AppShell({{super.key}});

  @override
  State<AppShell> createState() => _AppShellState();
}}

class _AppShellState extends State<AppShell> {{
  int _selectedIndex = 0;

  late final List<Widget> _pages = <Widget>[
    {("," + chr(10) + "    ").join(pages)},
  ];

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      body: IndexedStack(
        index: _selectedIndex,
        children: _pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {{
          setState(() => _selectedIndex = index);
        }},
        destinations: const <Widget>[
          {("," + chr(10) + "          ").join(destination_items)},
        ],
      ),
    );
  }}
}}
"""


def _theme_dart(theme_config: str | None) -> str:
    if theme_config and theme_config.strip():
        return theme_config.strip() + "\n"

    return """import 'package:flutter/material.dart';

class AppTheme {
  static const Color primary = Color(0xFF2563EB);
  static const Color secondary = Color(0xFF0F172A);
  static const Color appBackground = Color(0xFFF8FAFC);
  static const Color appSurface = Color(0xFFFFFFFF);
  static const Color appError = Color(0xFFDC2626);

  static ThemeData light() {
    final colorScheme = ColorScheme.fromSeed(seedColor: primary);
    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: appBackground,
    );
  }
}
"""


def _app_scaffold_dart() -> str:
    return """import 'package:flutter/material.dart';

class AppScaffold extends StatelessWidget {
  const AppScaffold({
    super.key,
    required this.title,
    required this.child,
    this.subtitle,
  });

  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return SafeArea(
      child: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 20, 16, 12),
            sliver: SliverToBoxAdapter(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (subtitle != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      subtitle!,
                      style: textTheme.bodyMedium?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
            sliver: SliverToBoxAdapter(child: child),
          ),
        ],
      ),
    );
  }
}
"""


def _feature_card_dart() -> str:
    return """import 'package:flutter/material.dart';

class FeatureCard extends StatelessWidget {
  const FeatureCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(icon, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(subtitle),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }
}
"""


def _state_view_dart() -> str:
    return """import 'package:flutter/material.dart';

class StateView extends StatelessWidget {
  const StateView({
    super.key,
    required this.title,
    required this.description,
    this.icon = Icons.info_outline,
    this.actionLabel,
    this.onAction,
  });

  final String title;
  final String description;
  final IconData icon;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 40),
            const SizedBox(height: 12),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              description,
              textAlign: TextAlign.center,
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: onAction,
                child: Text(actionLabel!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
"""


def _home_screen_dart(app_input: dict[str, Any], feature_keys: list[str]) -> str:
    name = _dart_string(app_input["name"])
    description = _dart_string(app_input["description"])
    feature_cards = "\n".join(
        f"""FeatureCard(
          title: '{_dart_string(_title(feature))}',
          subtitle: '{_dart_string(_feature_subtitle(feature))}',
          icon: {_feature_icon(feature)},
        ),
        const SizedBox(height: 12),"""
        for feature in feature_keys
    )
    return f"""import 'package:flutter/material.dart';
import 'package:{_package_name(app_input)}/shared/widgets/app_scaffold.dart';
import 'package:{_package_name(app_input)}/shared/widgets/feature_card.dart';

class HomeScreen extends StatelessWidget {{
  const HomeScreen({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return AppScaffold(
      title: '{name}',
      subtitle: '{description}',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          {feature_cards}
        ],
      ),
    );
  }}
}}
"""


def _feature_screen_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    title = _title(feature)
    package = _package_name(app_input)
    header_widget = _feature_header_widget(feature, title)
    return f"""import 'package:flutter/material.dart';
import 'package:{package}/core/di/app_dependencies.dart';
import 'package:{package}/features/{feature}/data/datasources/{feature}_local_data_source.dart';
import 'package:{package}/features/{feature}/data/datasources/{feature}_remote_data_source.dart';
import 'package:{package}/features/{feature}/data/repositories/{feature}_repository_impl.dart';
import 'package:{package}/features/{feature}/domain/entities/{feature}_item.dart';
import 'package:{package}/features/{feature}/domain/usecases/get_{feature}_items.dart';
import 'package:{package}/features/{feature}/presentation/cubit/{feature}_cubit.dart';
import 'package:{package}/shared/widgets/app_scaffold.dart';
import 'package:{package}/shared/widgets/state_view.dart';

class {class_name}Screen extends StatefulWidget {{
  const {class_name}Screen({{super.key}});

  @override
  State<{class_name}Screen> createState() => _{class_name}ScreenState();
}}

class _{class_name}ScreenState extends State<{class_name}Screen> {{
  late final {class_name}Cubit _cubit;

  @override
  void initState() {{
    super.initState();
    final repository = {class_name}RepositoryImpl(
      remoteDataSource: {class_name}RemoteDataSource(
        apiClient: AppDependencies.apiClient,
      ),
      localDataSource: {class_name}LocalDataSource(),
    );
    _cubit = {class_name}Cubit(Get{class_name}Items(repository))
      ..addListener(_onStateChanged)
      ..loadItems();
  }}

  @override
  void dispose() {{
    _cubit
      ..removeListener(_onStateChanged)
      ..dispose();
    super.dispose();
  }}

  void _onStateChanged() {{
    if (mounted) {{
      setState(() {{}});
    }}
  }}

  @override
  Widget build(BuildContext context) {{
    final state = _cubit.state;
    return AppScaffold(
      title: '{title}',
      subtitle: 'Clean Architecture MVP flow for {title}.',
      child: _buildContent(state),
    );
  }}

  Widget _buildContent({class_name}State state) {{
    switch (state.status) {{
      case {class_name}Status.initial:
      case {class_name}Status.loading:
        return const StateView(
          title: 'Loading {title}',
          description: 'Preparing generated feature data.',
          icon: Icons.hourglass_empty,
        );
      case {class_name}Status.empty:
        return StateView(
          title: '{title} empty state',
          description: 'No generated {feature} data yet.',
          icon: {_feature_icon(feature)},
          actionLabel: 'Refresh',
          onAction: _cubit.loadItems,
        );
      case {class_name}Status.failure:
        return StateView(
          title: '{title} error',
          description: state.message ?? 'Unable to load {feature} data.',
          icon: Icons.error_outline,
          actionLabel: 'Retry',
          onAction: _cubit.loadItems,
        );
      case {class_name}Status.success:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            {header_widget}
            for (final item in state.items) _{class_name}ItemCard(item: item),
          ],
        );
    }}
  }}
}}

class _{class_name}ItemCard extends StatelessWidget {{
  const _{class_name}ItemCard({{required this.item}});

  final {class_name}Item item;

  @override
  Widget build(BuildContext context) {{
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              item.title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 8),
            Text(item.description),
          ],
        ),
      ),
    );
  }}
}}
"""


def _feature_entity_dart(feature: str) -> str:
    class_name = _class_name(feature)
    return f"""class {class_name}Item {{
  const {class_name}Item({{
    required this.id,
    required this.title,
    required this.description,
  }});

  final String id;
  final String title;
  final String description;
}}
"""


def _feature_model_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    return f"""import 'package:{package}/features/{feature}/domain/entities/{feature}_item.dart';

class {class_name}Model extends {class_name}Item {{
  const {class_name}Model({{
    required super.id,
    required super.title,
    required super.description,
  }});

  factory {class_name}Model.fromJson(Map<String, dynamic> json) {{
    return {class_name}Model(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
    );
  }}

  Map<String, dynamic> toJson() {{
    return <String, dynamic>{{
      'id': id,
      'title': title,
      'description': description,
    }};
  }}
}}
"""


def _feature_dto_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    return f"""import 'package:{package}/features/{feature}/data/models/{feature}_model.dart';

class {class_name}Dto {{
  const {class_name}Dto({{
    required this.id,
    required this.title,
    required this.description,
  }});

  final String id;
  final String title;
  final String description;

  factory {class_name}Dto.fromJson(Map<String, dynamic> json) {{
    return {class_name}Dto(
      id: (json['id'] ?? '').toString(),
      title: (json['title'] ?? json['name'] ?? 'Untitled {feature}').toString(),
      description: (json['description'] ?? '').toString(),
    );
  }}

  {class_name}Model toModel() {{
    return {class_name}Model(
      id: id,
      title: title,
      description: description,
    );
  }}
}}
"""


def _feature_remote_data_source_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    sample_items = _sample_items(feature)
    model_lines = ",\n".join(
        f"""      {class_name}Model(
        id: '{_dart_string(feature)}-{index}',
        title: '{_dart_string(title)}',
        description: '{_dart_string(description)}',
      )"""
        for index, (title, description) in enumerate(sample_items, start=1)
    )
    return f"""import 'package:{package}/core/api/api_client.dart';
import 'package:{package}/core/config/app_config.dart';
import 'package:{package}/features/{feature}/data/dtos/{feature}_dto.dart';
import 'package:{package}/features/{feature}/data/models/{feature}_model.dart';

class {class_name}RemoteDataSource {{
  {class_name}RemoteDataSource({{ApiClient? apiClient}})
      : _apiClient = apiClient ?? ApiClient();

  final ApiClient _apiClient;

  Future<List<{class_name}Model>> fetchItems() async {{
    if (!AppConfig.useBackendApi) {{
      return _seedItems();
    }}

    try {{
      final jsonItems = await _apiClient.getList('/api/{feature}');
      return jsonItems
          .map({class_name}Dto.fromJson)
          .map(({class_name}Dto dto) => dto.toModel())
          .toList(growable: false);
    }} catch (_) {{
      return _seedItems();
    }}
  }}

  Future<List<{class_name}Model>> _seedItems() async {{
    await Future<void>.delayed(const Duration(milliseconds: 150));
    return const <{class_name}Model>[
{model_lines},
    ];
  }}
}}
"""


def _feature_local_data_source_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    return f"""import 'package:{package}/features/{feature}/data/models/{feature}_model.dart';

class {class_name}LocalDataSource {{
  List<{class_name}Model> _cachedItems = const <{class_name}Model>[];

  List<{class_name}Model> readItems() {{
    return _cachedItems;
  }}

  Future<void> cacheItems(List<{class_name}Model> items) async {{
    _cachedItems = List<{class_name}Model>.unmodifiable(items);
  }}
}}
"""


def _feature_repository_contract_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    return f"""import 'package:{package}/features/{feature}/domain/entities/{feature}_item.dart';

abstract class {class_name}Repository {{
  Future<List<{class_name}Item>> getItems();
}}
"""


def _feature_repository_impl_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    return f"""import 'package:{package}/features/{feature}/data/datasources/{feature}_local_data_source.dart';
import 'package:{package}/features/{feature}/data/datasources/{feature}_remote_data_source.dart';
import 'package:{package}/features/{feature}/domain/entities/{feature}_item.dart';
import 'package:{package}/features/{feature}/domain/repositories/{feature}_repository.dart';

class {class_name}RepositoryImpl implements {class_name}Repository {{
  const {class_name}RepositoryImpl({{
    required this.remoteDataSource,
    required this.localDataSource,
  }});

  final {class_name}RemoteDataSource remoteDataSource;
  final {class_name}LocalDataSource localDataSource;

  @override
  Future<List<{class_name}Item>> getItems() async {{
    try {{
      final items = await remoteDataSource.fetchItems();
      await localDataSource.cacheItems(items);
      return items;
    }} catch (_) {{
      return localDataSource.readItems();
    }}
  }}
}}
"""


def _feature_usecase_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    return f"""import 'package:{package}/features/{feature}/domain/entities/{feature}_item.dart';
import 'package:{package}/features/{feature}/domain/repositories/{feature}_repository.dart';

class Get{class_name}Items {{
  const Get{class_name}Items(this.repository);

  final {class_name}Repository repository;

  Future<List<{class_name}Item>> call() {{
    return repository.getItems();
  }}
}}
"""


def _feature_cubit_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    return f"""import 'package:flutter/foundation.dart';
import 'package:{package}/features/{feature}/domain/entities/{feature}_item.dart';
import 'package:{package}/features/{feature}/domain/usecases/get_{feature}_items.dart';

enum {class_name}Status {{ initial, loading, success, empty, failure }}

class {class_name}State {{
  const {class_name}State({{
    required this.status,
    required this.items,
    this.message,
  }});

  factory {class_name}State.initial() {{
    return const {class_name}State(
      status: {class_name}Status.initial,
      items: <{class_name}Item>[],
    );
  }}

  final {class_name}Status status;
  final List<{class_name}Item> items;
  final String? message;

  {class_name}State copyWith({{
    {class_name}Status? status,
    List<{class_name}Item>? items,
    String? message,
  }}) {{
    return {class_name}State(
      status: status ?? this.status,
      items: items ?? this.items,
      message: message ?? this.message,
    );
  }}
}}

class {class_name}Cubit extends ChangeNotifier {{
  {class_name}Cubit(this.getItems);

  final Get{class_name}Items getItems;
  {class_name}State _state = {class_name}State.initial();

  {class_name}State get state => _state;

  Future<void> loadItems() async {{
    _emit(_state.copyWith(status: {class_name}Status.loading));
    try {{
      final items = await getItems();
      _emit(
        _state.copyWith(
          status: items.isEmpty ? {class_name}Status.empty : {class_name}Status.success,
          items: items,
        ),
      );
    }} catch (error) {{
      _emit(
        _state.copyWith(
          status: {class_name}Status.failure,
          message: error.toString(),
        ),
      );
    }}
  }}

  void _emit({class_name}State state) {{
    _state = state;
    notifyListeners();
  }}
}}
"""


def _settings_screen_dart(app_input: dict[str, Any]) -> str:
    return f"""import 'package:flutter/material.dart';
import 'package:{_package_name(app_input)}/shared/widgets/app_scaffold.dart';

class SettingsScreen extends StatelessWidget {{
  const SettingsScreen({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return const AppScaffold(
      title: 'Settings',
      subtitle: 'Generated app configuration and diagnostics.',
      child: Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Text('Settings will be expanded after the MVP flow is stable.'),
        ),
      ),
    );
  }}
}}
"""


def _analysis_options() -> str:
    return """analyzer:
  errors:
    todo: ignore
"""


def _readme(app_input: dict[str, Any]) -> str:
    return f"""# {app_input["name"]}

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
"""


def _frontend_integration_report(
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
    feature_keys: list[str],
) -> str:
    product_spec_path = docs_dir / "product_spec.json"
    openapi_path = docs_dir / "openapi.yaml"
    product_schema_version = "unknown"
    if product_spec_path.exists():
        product_spec = json.loads(product_spec_path.read_text(encoding="utf-8"))
        product_schema_version = str(product_spec.get("schema_version", "unknown"))

    endpoints = "\n".join(f"- `GET /api/{feature}`" for feature in feature_keys)
    generated_files = [
        "source/lib/core/api/api_client.dart",
        "source/lib/core/config/app_config.dart",
        "source/lib/core/di/app_dependencies.dart",
        "source/.env.example",
        *[
            f"source/lib/features/{feature}/data/dtos/{feature}_dto.dart"
            for feature in feature_keys
        ],
        *[
            f"source/lib/features/{feature}/data/datasources/{feature}_remote_data_source.dart"
            for feature in feature_keys
        ],
    ]
    generated_file_text = "\n".join(f"- `{path}`" for path in generated_files)
    openapi_status = "FOUND" if openapi_path.exists() else "MISSING"

    return f"""# Frontend Integration Report: {app_input["name"]}

## Status

- Phase: J - Flutter API Integration
- Source: `{source_dir}`
- Product spec schema: `{product_schema_version}`
- OpenAPI contract: {openapi_status} at `{openapi_path}`

## Backend Contract Used

{endpoints or "- No feature endpoints detected."}

## Generated Frontend Integration

{generated_file_text}

## Runtime Configuration

- `API_BASE_URL`: backend base URL.
- `APP_ENV`: local/staging/production marker.
- `USE_BACKEND_API`: set `true` to call generated FastAPI endpoints.

## Verification Intent

- Widget tests can run without a backend by using generated seed fallback.
- API client contract tests use an injected fake HTTP client.
- Production/staging runs should pass `--dart-define=USE_BACKEND_API=true`.
"""


def _app_widget_test_dart(app_input: dict[str, Any], feature_keys: list[str]) -> str:
    package = _package_name(app_input)
    app_name = _dart_string(app_input["name"])
    imports = [
        "import 'package:flutter/material.dart';",
        "import 'package:flutter_test/flutter_test.dart';",
        f"import 'package:{package}/app.dart';",
    ]
    for feature in feature_keys:
        imports.append(
            f"import 'package:{package}/features/{feature}/presentation/screens/{feature}_screen.dart';"
        )

    feature_screen_tests = "\n\n".join(
        f"""  testWidgets('renders {_dart_string(_title(feature))} screen data', (tester) async {{
    await tester.pumpWidget(const MaterialApp(home: {_class_name(feature)}Screen()));

    expect(find.text('Loading {_dart_string(_title(feature))}'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 250));
    await tester.pumpAndSettle();

    expect(find.text('{_dart_string(_title(feature))}'), findsOneWidget);
    expect(find.text('{_dart_string(_sample_items(feature)[0][0])}'), findsOneWidget);
  }});"""
        for feature in feature_keys
    )

    first_feature_assertion = ""
    if feature_keys:
        first_feature = feature_keys[0]
        first_feature_assertion = f"""

    expect(find.text('{_dart_string(_title(first_feature))}'), findsWidgets);"""

    return f"""{chr(10).join(imports)}

void main() {{
  testWidgets('renders generated app shell and home content', (tester) async {{
    await tester.pumpWidget(const GeneratedApp());
    await tester.pump(const Duration(milliseconds: 250));
    await tester.pumpAndSettle();

    expect(find.text('{app_name}'), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);{first_feature_assertion}
  }});

{feature_screen_tests}
}}
"""


def _api_client_test_dart(app_input: dict[str, Any]) -> str:
    package = _package_name(app_input)
    return f"""import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:{package}/core/api/api_client.dart';

void main() {{
  test('ApiClient decodes list responses', () async {{
    final client = ApiClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((request) async {{
        expect(request.url.path, '/api/todo');
        return http.Response(
          '[{{"id":"todo-1","title":"Todo","description":"One item"}}]',
          200,
        );
      }}),
    );

    final result = await client.getList('/api/todo');

    expect(result, hasLength(1));
    expect(result.first['title'], 'Todo');
  }});

  test('ApiClient throws on failed responses', () async {{
    final client = ApiClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((request) async => http.Response('bad', 500)),
    );

    expect(
      () => client.getList('/api/todo'),
      throwsA(isA<ApiException>()),
    );
  }});
}}
"""


def _feature_logic_test_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    item_title = _dart_string(_sample_items(feature)[0][0])
    return f"""import 'package:flutter_test/flutter_test.dart';
import 'package:{package}/features/{feature}/domain/entities/{feature}_item.dart';
import 'package:{package}/features/{feature}/domain/repositories/{feature}_repository.dart';
import 'package:{package}/features/{feature}/domain/usecases/get_{feature}_items.dart';
import 'package:{package}/features/{feature}/presentation/cubit/{feature}_cubit.dart';

class Fake{class_name}Repository implements {class_name}Repository {{
  Fake{class_name}Repository({{required this.items, this.error}});

  final List<{class_name}Item> items;
  final Object? error;

  @override
  Future<List<{class_name}Item>> getItems() async {{
    if (error != null) {{
      throw error!;
    }}
    return items;
  }}
}}

void main() {{
  const item = {class_name}Item(
    id: '{_dart_string(feature)}-test',
    title: '{item_title}',
    description: 'Generated test item',
  );

  test('Get{class_name}Items returns repository items', () async {{
    final usecase = Get{class_name}Items(
      Fake{class_name}Repository(items: const <{class_name}Item>[item]),
    );

    final result = await usecase();

    expect(result, hasLength(1));
    expect(result.first.title, '{item_title}');
  }});

  test('{class_name}Cubit emits success when data exists', () async {{
    final cubit = {class_name}Cubit(
      Get{class_name}Items(
        Fake{class_name}Repository(items: const <{class_name}Item>[item]),
      ),
    );
    final statuses = <{class_name}Status>[];
    cubit.addListener(() => statuses.add(cubit.state.status));

    await cubit.loadItems();

    expect(statuses, containsAllInOrder(<{class_name}Status>[
      {class_name}Status.loading,
      {class_name}Status.success,
    ]));
    expect(cubit.state.items, hasLength(1));

    cubit.dispose();
  }});

  test('{class_name}Cubit emits empty when repository has no data', () async {{
    final cubit = {class_name}Cubit(
      Get{class_name}Items(
        Fake{class_name}Repository(items: const <{class_name}Item>[]),
      ),
    );

    await cubit.loadItems();

    expect(cubit.state.status, {class_name}Status.empty);

    cubit.dispose();
  }});

  test('{class_name}Cubit emits failure when repository throws', () async {{
    final cubit = {class_name}Cubit(
      Get{class_name}Items(
        Fake{class_name}Repository(
          items: const <{class_name}Item>[],
          error: StateError('boom'),
        ),
      ),
    );

    await cubit.loadItems();

    expect(cubit.state.status, {class_name}Status.failure);
    expect(cubit.state.message, contains('boom'));

    cubit.dispose();
  }});
}}
"""


def _feature_data_test_dart(app_input: dict[str, Any], feature: str) -> str:
    class_name = _class_name(feature)
    package = _package_name(app_input)
    item_title = _dart_string(_sample_items(feature)[0][0])
    return f"""import 'package:flutter_test/flutter_test.dart';
import 'package:{package}/features/{feature}/data/datasources/{feature}_local_data_source.dart';
import 'package:{package}/features/{feature}/data/datasources/{feature}_remote_data_source.dart';
import 'package:{package}/features/{feature}/data/dtos/{feature}_dto.dart';
import 'package:{package}/features/{feature}/data/models/{feature}_model.dart';
import 'package:{package}/features/{feature}/data/repositories/{feature}_repository_impl.dart';

void main() {{
  test('{class_name}Dto maps backend JSON to model', () {{
    final dto = {class_name}Dto.fromJson(const <String, dynamic>{{
      'id': '{feature}-json',
      'title': '{item_title}',
      'description': 'Mapped from backend',
    }});

    final model = dto.toModel();

    expect(model.id, '{feature}-json');
    expect(model.title, '{item_title}');
    expect(model.description, 'Mapped from backend');
  }});

  test('{class_name}Model serializes to JSON', () {{
    const model = {class_name}Model(
      id: '{feature}-model',
      title: '{item_title}',
      description: 'Serializable model',
    );

    expect(model.toJson(), <String, dynamic>{{
      'id': '{feature}-model',
      'title': '{item_title}',
      'description': 'Serializable model',
    }});
  }});

  test('{class_name}LocalDataSource caches immutable items', () async {{
    final dataSource = {class_name}LocalDataSource();
    const items = <{class_name}Model>[
      {class_name}Model(
        id: '{feature}-cached',
        title: '{item_title}',
        description: 'Cached item',
      ),
    ];

    await dataSource.cacheItems(items);

    expect(dataSource.readItems(), hasLength(1));
    expect(() => dataSource.readItems().add(items.first), throwsUnsupportedError);
  }});

  test('{class_name}RemoteDataSource returns seed items when API mode is disabled', () async {{
    final dataSource = {class_name}RemoteDataSource();

    final items = await dataSource.fetchItems();

    expect(items, isNotEmpty);
    expect(items.first.title, '{item_title}');
  }});

  test('{class_name}RepositoryImpl caches remote items', () async {{
    final localDataSource = {class_name}LocalDataSource();
    final repository = {class_name}RepositoryImpl(
      remoteDataSource: {class_name}RemoteDataSource(),
      localDataSource: localDataSource,
    );

    final items = await repository.getItems();

    expect(items, isNotEmpty);
    expect(localDataSource.readItems(), hasLength(items.length));
  }});
}}
"""


def expected_source_paths(app_input: dict[str, Any]) -> list[str]:
    feature_keys = [_feature_key(feature) for feature in app_input.get("features", [])]
    if not feature_keys:
        feature_keys = ["home"]

    paths = [
        ".env.example",
        "pubspec.yaml",
        "analysis_options.yaml",
        "README.md",
        "lib/main.dart",
        "web/index.html",
        "lib/app.dart",
        "lib/core/api/api_client.dart",
        "lib/core/config/app_config.dart",
        "lib/core/di/app_dependencies.dart",
        "lib/core/theme/app_theme.dart",
        "lib/shared/widgets/app_scaffold.dart",
        "lib/shared/widgets/feature_card.dart",
        "lib/shared/widgets/state_view.dart",
        "lib/features/home/presentation/screens/home_screen.dart",
        "lib/features/settings/presentation/screens/settings_screen.dart",
        "test/app_widget_test.dart",
        "test/core/api/api_client_test.dart",
    ]
    for feature in feature_keys:
        paths.extend(
            [
                f"lib/features/{feature}/data/datasources/{feature}_remote_data_source.dart",
                f"lib/features/{feature}/data/datasources/{feature}_local_data_source.dart",
                f"lib/features/{feature}/data/dtos/{feature}_dto.dart",
                f"lib/features/{feature}/data/models/{feature}_model.dart",
                f"lib/features/{feature}/data/repositories/{feature}_repository_impl.dart",
                f"lib/features/{feature}/domain/entities/{feature}_item.dart",
                f"lib/features/{feature}/domain/repositories/{feature}_repository.dart",
                f"lib/features/{feature}/domain/usecases/get_{feature}_items.dart",
                f"lib/features/{feature}/presentation/cubit/{feature}_cubit.dart",
                f"test/features/{feature}/{feature}_logic_test.dart",
                f"test/features/{feature}/{feature}_data_test.dart",
            ]
        )
        paths.append(
            f"lib/features/{feature}/presentation/screens/{feature}_screen.dart"
        )
    return paths


def write_flutter_source(
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
) -> list[Path]:
    feature_keys = [_feature_key(feature) for feature in app_input.get("features", [])]
    if not feature_keys:
        feature_keys = ["home"]

    package = _package_name(app_input)
    theme_config_path = docs_dir / "theme_config.dart"
    theme_config = (
        theme_config_path.read_text(encoding="utf-8")
        if theme_config_path.exists()
        else None
    )

    paths = [
        _write(source_dir / ".env.example", _env_example()),
        _write(source_dir / "pubspec.yaml", _pubspec(app_input)),
        _write(source_dir / "analysis_options.yaml", _analysis_options()),
        _write(source_dir / "README.md", _readme(app_input)),
        _write(source_dir / "lib" / "main.dart", _main_dart(package)),
        _write(source_dir / "web" / "index.html", _web_index_html(app_input)),
        _write(source_dir / "lib" / "app.dart", _app_dart(app_input, feature_keys)),
        _write(source_dir / "lib" / "core" / "api" / "api_client.dart", _api_client_dart(app_input)),
        _write(source_dir / "lib" / "core" / "config" / "app_config.dart", _app_config_dart()),
        _write(source_dir / "lib" / "core" / "di" / "app_dependencies.dart", _app_dependencies_dart(app_input)),
        _write(
            source_dir / "lib" / "core" / "theme" / "app_theme.dart",
            _theme_dart(theme_config),
        ),
        _write(
            source_dir / "lib" / "shared" / "widgets" / "app_scaffold.dart",
            _app_scaffold_dart(),
        ),
        _write(
            source_dir / "lib" / "shared" / "widgets" / "feature_card.dart",
            _feature_card_dart(),
        ),
        _write(
            source_dir / "lib" / "shared" / "widgets" / "state_view.dart",
            _state_view_dart(),
        ),
        _write(
            source_dir
            / "lib"
            / "features"
            / "home"
            / "presentation"
            / "screens"
            / "home_screen.dart",
            _home_screen_dart(app_input, feature_keys),
        ),
        _write(
            source_dir
            / "lib"
            / "features"
            / "settings"
            / "presentation"
            / "screens"
            / "settings_screen.dart",
            _settings_screen_dart(app_input),
        ),
        _write(
            source_dir / "test" / "app_widget_test.dart",
            _app_widget_test_dart(app_input, feature_keys),
        ),
        _write(
            source_dir / "test" / "core" / "api" / "api_client_test.dart",
            _api_client_test_dart(app_input),
        ),
    ]

    for feature in feature_keys:
        paths.extend(
            [
                _write(
                    source_dir
                    / "lib"
                    / "features"
                    / feature
                    / "domain"
                    / "entities"
                    / f"{feature}_item.dart",
                    _feature_entity_dart(feature),
                ),
                _write(
                    source_dir
                    / "lib"
                    / "features"
                    / feature
                    / "data"
                    / "models"
                    / f"{feature}_model.dart",
                    _feature_model_dart(app_input, feature),
                ),
                _write(
                    source_dir
                    / "lib"
                    / "features"
                    / feature
                    / "data"
                    / "dtos"
                    / f"{feature}_dto.dart",
                    _feature_dto_dart(app_input, feature),
                ),
                _write(
                    source_dir
                    / "lib"
                    / "features"
                    / feature
                    / "data"
                    / "datasources"
                    / f"{feature}_remote_data_source.dart",
                    _feature_remote_data_source_dart(app_input, feature),
                ),
                _write(
                    source_dir
                    / "lib"
                    / "features"
                    / feature
                    / "data"
                    / "datasources"
                    / f"{feature}_local_data_source.dart",
                    _feature_local_data_source_dart(app_input, feature),
                ),
                _write(
                    source_dir
                    / "lib"
                    / "features"
                    / feature
                    / "domain"
                    / "repositories"
                    / f"{feature}_repository.dart",
                    _feature_repository_contract_dart(app_input, feature),
                ),
                _write(
                    source_dir
                    / "lib"
                    / "features"
                    / feature
                    / "data"
                    / "repositories"
                    / f"{feature}_repository_impl.dart",
                    _feature_repository_impl_dart(app_input, feature),
                ),
                _write(
                    source_dir
                    / "lib"
                    / "features"
                    / feature
                    / "domain"
                    / "usecases"
                    / f"get_{feature}_items.dart",
                    _feature_usecase_dart(app_input, feature),
                ),
                _write(
                    source_dir
                    / "lib"
                    / "features"
                    / feature
                    / "presentation"
                    / "cubit"
                    / f"{feature}_cubit.dart",
                    _feature_cubit_dart(app_input, feature),
                ),
            ]
        )
        paths.append(
            _write(
                source_dir
                / "lib"
                / "features"
                / feature
                / "presentation"
                / "screens"
                / f"{feature}_screen.dart",
                _feature_screen_dart(app_input, feature),
            )
        )
        paths.append(
            _write(
                source_dir
                / "test"
                / "features"
                / feature
                / f"{feature}_logic_test.dart",
                _feature_logic_test_dart(app_input, feature),
            )
        )
        paths.append(
            _write(
                source_dir
                / "test"
                / "features"
                / feature
                / f"{feature}_data_test.dart",
                _feature_data_test_dart(app_input, feature),
            )
        )

    paths.append(
        _write(
            docs_dir / "frontend_integration_report.md",
            _frontend_integration_report(app_input, docs_dir, source_dir, feature_keys),
        )
    )

    return paths
