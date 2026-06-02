import 'package:flutter_test/flutter_test.dart';
import 'package:test/features/todo/data/datasources/todo_local_data_source.dart';
import 'package:test/features/todo/data/datasources/todo_remote_data_source.dart';
import 'package:test/features/todo/data/dtos/todo_dto.dart';
import 'package:test/features/todo/data/models/todo_model.dart';
import 'package:test/features/todo/data/repositories/todo_repository_impl.dart';

void main() {
  test('TodoDto maps backend JSON to model', () {
    final dto = TodoDto.fromJson(const <String, dynamic>{
      'id': 'todo-json',
      'title': 'Plan MVP scope',
      'description': 'Mapped from backend',
    });

    final model = dto.toModel();

    expect(model.id, 'todo-json');
    expect(model.title, 'Plan MVP scope');
    expect(model.description, 'Mapped from backend');
  });

  test('TodoModel serializes to JSON', () {
    const model = TodoModel(
      id: 'todo-model',
      title: 'Plan MVP scope',
      description: 'Serializable model',
    );

    expect(model.toJson(), <String, dynamic>{
      'id': 'todo-model',
      'title': 'Plan MVP scope',
      'description': 'Serializable model',
    });
  });

  test('TodoLocalDataSource caches immutable items', () async {
    final dataSource = TodoLocalDataSource();
    const items = <TodoModel>[
      TodoModel(
        id: 'todo-cached',
        title: 'Plan MVP scope',
        description: 'Cached item',
      ),
    ];

    await dataSource.cacheItems(items);

    expect(dataSource.readItems(), hasLength(1));
    expect(() => dataSource.readItems().add(items.first), throwsUnsupportedError);
  });

  test('TodoRemoteDataSource returns seed items when API mode is disabled', () async {
    final dataSource = TodoRemoteDataSource();

    final items = await dataSource.fetchItems();

    expect(items, isNotEmpty);
    expect(items.first.title, 'Plan MVP scope');
  });

  test('TodoRepositoryImpl caches remote items', () async {
    final localDataSource = TodoLocalDataSource();
    final repository = TodoRepositoryImpl(
      remoteDataSource: TodoRemoteDataSource(),
      localDataSource: localDataSource,
    );

    final items = await repository.getItems();

    expect(items, isNotEmpty);
    expect(localDataSource.readItems(), hasLength(items.length));
  });
}
