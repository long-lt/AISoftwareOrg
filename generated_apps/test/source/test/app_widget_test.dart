import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:test/app.dart';
import 'package:test/features/todo/presentation/screens/todo_screen.dart';
import 'package:test/features/dashboard/presentation/screens/dashboard_screen.dart';
import 'package:test/features/settings/presentation/screens/settings_screen.dart';

void main() {
  testWidgets('renders generated app shell and home content', (tester) async {
    await tester.pumpWidget(const GeneratedApp());
    await tester.pump(const Duration(milliseconds: 250));
    await tester.pumpAndSettle();

    expect(find.text('Test'), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);

    expect(find.text('Todo'), findsWidgets);
  });

  testWidgets('renders Todo screen data', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: TodoScreen()));

    expect(find.text('Loading Todo'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 250));
    await tester.pumpAndSettle();

    expect(find.text('Todo'), findsOneWidget);
    expect(find.text('Plan MVP scope'), findsOneWidget);
  });

  testWidgets('renders Dashboard screen data', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: DashboardScreen()));

    expect(find.text('Loading Dashboard'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 250));
    await tester.pumpAndSettle();

    expect(find.text('Dashboard'), findsOneWidget);
    expect(find.text('Dashboard item 1'), findsOneWidget);
  });

  testWidgets('renders Settings screen data', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: SettingsScreen()));

    expect(find.text('Loading Settings'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 250));
    await tester.pumpAndSettle();

    expect(find.text('Settings'), findsOneWidget);
    expect(find.text('Settings item 1'), findsOneWidget);
  });
}
