import 'package:flutter_test/flutter_test.dart';
import 'package:test/features/settings/domain/entities/settings_item.dart';
import 'package:test/features/settings/domain/repositories/settings_repository.dart';
import 'package:test/features/settings/domain/usecases/get_settings_items.dart';
import 'package:test/features/settings/presentation/cubit/settings_cubit.dart';

class FakeSettingsRepository implements SettingsRepository {
  FakeSettingsRepository({required this.items, this.error});

  final List<SettingsItem> items;
  final Object? error;

  @override
  Future<List<SettingsItem>> getItems() async {
    if (error != null) {
      throw error!;
    }
    return items;
  }
}

void main() {
  const item = SettingsItem(
    id: 'settings-test',
    title: 'Settings item 1',
    description: 'Generated test item',
  );

  test('GetSettingsItems returns repository items', () async {
    final usecase = GetSettingsItems(
      FakeSettingsRepository(items: const <SettingsItem>[item]),
    );

    final result = await usecase();

    expect(result, hasLength(1));
    expect(result.first.title, 'Settings item 1');
  });

  test('SettingsCubit emits success when data exists', () async {
    final cubit = SettingsCubit(
      GetSettingsItems(
        FakeSettingsRepository(items: const <SettingsItem>[item]),
      ),
    );
    final statuses = <SettingsStatus>[];
    cubit.addListener(() => statuses.add(cubit.state.status));

    await cubit.loadItems();

    expect(statuses, containsAllInOrder(<SettingsStatus>[
      SettingsStatus.loading,
      SettingsStatus.success,
    ]));
    expect(cubit.state.items, hasLength(1));

    cubit.dispose();
  });

  test('SettingsCubit emits empty when repository has no data', () async {
    final cubit = SettingsCubit(
      GetSettingsItems(
        FakeSettingsRepository(items: const <SettingsItem>[]),
      ),
    );

    await cubit.loadItems();

    expect(cubit.state.status, SettingsStatus.empty);

    cubit.dispose();
  });

  test('SettingsCubit emits failure when repository throws', () async {
    final cubit = SettingsCubit(
      GetSettingsItems(
        FakeSettingsRepository(
          items: const <SettingsItem>[],
          error: StateError('boom'),
        ),
      ),
    );

    await cubit.loadItems();

    expect(cubit.state.status, SettingsStatus.failure);
    expect(cubit.state.message, contains('boom'));

    cubit.dispose();
  });
}
