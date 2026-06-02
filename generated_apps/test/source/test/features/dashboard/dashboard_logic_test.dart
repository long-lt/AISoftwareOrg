import 'package:flutter_test/flutter_test.dart';
import 'package:test/features/dashboard/domain/entities/dashboard_item.dart';
import 'package:test/features/dashboard/domain/repositories/dashboard_repository.dart';
import 'package:test/features/dashboard/domain/usecases/get_dashboard_items.dart';
import 'package:test/features/dashboard/presentation/cubit/dashboard_cubit.dart';

class FakeDashboardRepository implements DashboardRepository {
  FakeDashboardRepository({required this.items, this.error});

  final List<DashboardItem> items;
  final Object? error;

  @override
  Future<List<DashboardItem>> getItems() async {
    if (error != null) {
      throw error!;
    }
    return items;
  }
}

void main() {
  const item = DashboardItem(
    id: 'dashboard-test',
    title: 'Dashboard item 1',
    description: 'Generated test item',
  );

  test('GetDashboardItems returns repository items', () async {
    final usecase = GetDashboardItems(
      FakeDashboardRepository(items: const <DashboardItem>[item]),
    );

    final result = await usecase();

    expect(result, hasLength(1));
    expect(result.first.title, 'Dashboard item 1');
  });

  test('DashboardCubit emits success when data exists', () async {
    final cubit = DashboardCubit(
      GetDashboardItems(
        FakeDashboardRepository(items: const <DashboardItem>[item]),
      ),
    );
    final statuses = <DashboardStatus>[];
    cubit.addListener(() => statuses.add(cubit.state.status));

    await cubit.loadItems();

    expect(statuses, containsAllInOrder(<DashboardStatus>[
      DashboardStatus.loading,
      DashboardStatus.success,
    ]));
    expect(cubit.state.items, hasLength(1));

    cubit.dispose();
  });

  test('DashboardCubit emits empty when repository has no data', () async {
    final cubit = DashboardCubit(
      GetDashboardItems(
        FakeDashboardRepository(items: const <DashboardItem>[]),
      ),
    );

    await cubit.loadItems();

    expect(cubit.state.status, DashboardStatus.empty);

    cubit.dispose();
  });

  test('DashboardCubit emits failure when repository throws', () async {
    final cubit = DashboardCubit(
      GetDashboardItems(
        FakeDashboardRepository(
          items: const <DashboardItem>[],
          error: StateError('boom'),
        ),
      ),
    );

    await cubit.loadItems();

    expect(cubit.state.status, DashboardStatus.failure);
    expect(cubit.state.message, contains('boom'));

    cubit.dispose();
  });
}
