import 'package:flutter_test/flutter_test.dart';
import 'package:test/features/todo/domain/entities/todo_item.dart';
import 'package:test/features/todo/domain/repositories/todo_repository.dart';
import 'package:test/features/todo/domain/usecases/get_todo_items.dart';
import 'package:test/features/todo/presentation/cubit/todo_cubit.dart';

class FakeTodoRepository implements TodoRepository {
  FakeTodoRepository({required this.items, this.error});

  final List<TodoItem> items;
  final Object? error;

  @override
  Future<List<TodoItem>> getItems() async {
    if (error != null) {
      throw error!;
    }
    return items;
  }
}

void main() {
  const item = TodoItem(
    id: 'todo-test',
    title: 'Plan MVP scope',
    description: 'Generated test item',
  );

  test('GetTodoItems returns repository items', () async {
    final usecase = GetTodoItems(
      FakeTodoRepository(items: const <TodoItem>[item]),
    );

    final result = await usecase();

    expect(result, hasLength(1));
    expect(result.first.title, 'Plan MVP scope');
  });

  test('TodoCubit emits success when data exists', () async {
    final cubit = TodoCubit(
      GetTodoItems(
        FakeTodoRepository(items: const <TodoItem>[item]),
      ),
    );
    final statuses = <TodoStatus>[];
    cubit.addListener(() => statuses.add(cubit.state.status));

    await cubit.loadItems();

    expect(statuses, containsAllInOrder(<TodoStatus>[
      TodoStatus.loading,
      TodoStatus.success,
    ]));
    expect(cubit.state.items, hasLength(1));

    cubit.dispose();
  });

  test('TodoCubit emits empty when repository has no data', () async {
    final cubit = TodoCubit(
      GetTodoItems(
        FakeTodoRepository(items: const <TodoItem>[]),
      ),
    );

    await cubit.loadItems();

    expect(cubit.state.status, TodoStatus.empty);

    cubit.dispose();
  });

  test('TodoCubit emits failure when repository throws', () async {
    final cubit = TodoCubit(
      GetTodoItems(
        FakeTodoRepository(
          items: const <TodoItem>[],
          error: StateError('boom'),
        ),
      ),
    );

    await cubit.loadItems();

    expect(cubit.state.status, TodoStatus.failure);
    expect(cubit.state.message, contains('boom'));

    cubit.dispose();
  });
}
