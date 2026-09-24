import 'package:flutter_test/flutter_test.dart';
import 'package:gestion_stock_app/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const GestionStockApp());
    expect(find.text('Kal3iya Stock'), findsOneWidget);
  });
}
