import 'package:flutter_test/flutter_test.dart';
import 'package:suivi_budget_app/main.dart';

void main() {
  testWidgets('App launches smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const SuiviBudgetApp());
    expect(find.byType(SuiviBudgetApp), findsOneWidget);
  });
}
