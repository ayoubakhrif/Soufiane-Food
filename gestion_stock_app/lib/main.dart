import 'package:flutter/material.dart';
import 'models/agent.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'services/local_storage_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final savedAgent = await LocalStorageService.getAgentSession();
  runApp(GestionStockApp(initialAgent: savedAgent));
}

class GestionStockApp extends StatelessWidget {
  final Agent? initialAgent;

  const GestionStockApp({super.key, this.initialAgent});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Kal3iya Stock',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue.shade800),
        useMaterial3: true,
        fontFamily: 'Roboto',
      ),
      home: initialAgent != null
          ? HomeScreen(agent: initialAgent!)
          : const LoginScreen(),
    );
  }
}
