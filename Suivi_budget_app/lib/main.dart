import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'models/user_session.dart';
import 'screens/login_screen.dart';
import 'screens/main_navigation_screen.dart';
import 'services/storage_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('fr_FR', null);
  final savedSession = await StorageService.getSession();

  runApp(SuiviBudgetApp(initialSession: savedSession));
}

class SuiviBudgetApp extends StatelessWidget {
  final UserSession? initialSession;

  const SuiviBudgetApp({
    super.key,
    this.initialSession,
  });

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Suivi Budget',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0284C7),
          primary: const Color(0xFF0284C7),
        ),
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          elevation: 0,
          scrolledUnderElevation: 0,
          iconTheme: IconThemeData(color: Color(0xFF0F172A)),
        ),
      ),
      home: initialSession != null
          ? MainNavigationScreen(session: initialSession!)
          : const LoginScreen(),
    );
  }
}
