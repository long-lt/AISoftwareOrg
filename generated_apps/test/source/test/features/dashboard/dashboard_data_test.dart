import 'package:flutter_test/flutter_test.dart';
import 'package:test/features/dashboard/data/datasources/dashboard_local_data_source.dart';
import 'package:test/features/dashboard/data/datasources/dashboard_remote_data_source.dart';
import 'package:test/features/dashboard/data/dtos/dashboard_dto.dart';
import 'package:test/features/dashboard/data/models/dashboard_model.dart';
import 'package:test/features/dashboard/data/repositories/dashboard_repository_impl.dart';

void main() {
  test('DashboardDto maps backend JSON to model', () {
    final dto = DashboardDto.fromJson(const <String, dynamic>{
      'id': 'dashboard-json',
      'title': 'Dashboard item 1',
      'description': 'Mapped from backend',
    });

    final model = dto.toModel();

    expect(model.id, 'dashboard-json');
    expect(model.title, 'Dashboard item 1');
    expect(model.description, 'Mapped from backend');
  });

  test('DashboardModel serializes to JSON', () {
    const model = DashboardModel(
      id: 'dashboard-model',
      title: 'Dashboard item 1',
      description: 'Serializable model',
    );

    expect(model.toJson(), <String, dynamic>{
      'id': 'dashboard-model',
      'title': 'Dashboard item 1',
      'description': 'Serializable model',
    });
  });

  test('DashboardLocalDataSource caches immutable items', () async {
    final dataSource = DashboardLocalDataSource();
    const items = <DashboardModel>[
      DashboardModel(
        id: 'dashboard-cached',
        title: 'Dashboard item 1',
        description: 'Cached item',
      ),
    ];

    await dataSource.cacheItems(items);

    expect(dataSource.readItems(), hasLength(1));
    expect(() => dataSource.readItems().add(items.first), throwsUnsupportedError);
  });

  test('DashboardRemoteDataSource returns seed items when API mode is disabled', () async {
    final dataSource = DashboardRemoteDataSource();

    final items = await dataSource.fetchItems();

    expect(items, isNotEmpty);
    expect(items.first.title, 'Dashboard item 1');
  });

  test('DashboardRepositoryImpl caches remote items', () async {
    final localDataSource = DashboardLocalDataSource();
    final repository = DashboardRepositoryImpl(
      remoteDataSource: DashboardRemoteDataSource(),
      localDataSource: localDataSource,
    );

    final items = await repository.getItems();

    expect(items, isNotEmpty);
    expect(localDataSource.readItems(), hasLength(items.length));
  });
}
