import 'package:flutter_test/flutter_test.dart';
import 'package:test/features/settings/data/datasources/settings_local_data_source.dart';
import 'package:test/features/settings/data/datasources/settings_remote_data_source.dart';
import 'package:test/features/settings/data/dtos/settings_dto.dart';
import 'package:test/features/settings/data/models/settings_model.dart';
import 'package:test/features/settings/data/repositories/settings_repository_impl.dart';

void main() {
  test('SettingsDto maps backend JSON to model', () {
    final dto = SettingsDto.fromJson(const <String, dynamic>{
      'id': 'settings-json',
      'title': 'Settings item 1',
      'description': 'Mapped from backend',
    });

    final model = dto.toModel();

    expect(model.id, 'settings-json');
    expect(model.title, 'Settings item 1');
    expect(model.description, 'Mapped from backend');
  });

  test('SettingsModel serializes to JSON', () {
    const model = SettingsModel(
      id: 'settings-model',
      title: 'Settings item 1',
      description: 'Serializable model',
    );

    expect(model.toJson(), <String, dynamic>{
      'id': 'settings-model',
      'title': 'Settings item 1',
      'description': 'Serializable model',
    });
  });

  test('SettingsLocalDataSource caches immutable items', () async {
    final dataSource = SettingsLocalDataSource();
    const items = <SettingsModel>[
      SettingsModel(
        id: 'settings-cached',
        title: 'Settings item 1',
        description: 'Cached item',
      ),
    ];

    await dataSource.cacheItems(items);

    expect(dataSource.readItems(), hasLength(1));
    expect(() => dataSource.readItems().add(items.first), throwsUnsupportedError);
  });

  test('SettingsRemoteDataSource returns seed items when API mode is disabled', () async {
    final dataSource = SettingsRemoteDataSource();

    final items = await dataSource.fetchItems();

    expect(items, isNotEmpty);
    expect(items.first.title, 'Settings item 1');
  });

  test('SettingsRepositoryImpl caches remote items', () async {
    final localDataSource = SettingsLocalDataSource();
    final repository = SettingsRepositoryImpl(
      remoteDataSource: SettingsRemoteDataSource(),
      localDataSource: localDataSource,
    );

    final items = await repository.getItems();

    expect(items, isNotEmpty);
    expect(localDataSource.readItems(), hasLength(items.length));
  });
}
