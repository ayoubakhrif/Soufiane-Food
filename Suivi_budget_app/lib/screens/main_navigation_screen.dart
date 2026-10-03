import 'package:flutter/material.dart';
import '../models/user_session.dart';
import 'dashboard_screen.dart';
import 'add_expense_screen.dart';
import 'analytics_screen.dart';
import 'expense_history_screen.dart';

class MainNavigationScreen extends StatefulWidget {
  final UserSession session;

  final int initialIndex;

  const MainNavigationScreen({
    super.key,
    required this.session,
    this.initialIndex = 1, // Ouverture par défaut sur "Nouvelle Sortie"
  });

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  late int _currentIndex;
  final GlobalKey<DashboardScreenState> _dashboardKey = GlobalKey<DashboardScreenState>();
  final GlobalKey<AnalyticsScreenState> _analyticsKey = GlobalKey<AnalyticsScreenState>();
  final GlobalKey<ExpenseHistoryScreenState> _historyKey = GlobalKey<ExpenseHistoryScreenState>();

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialIndex;
  }

  void _onExpenseAdded() {
    // Rafraîchir les données du dashboard, des analyses et de l'historique
    _dashboardKey.currentState?.refresh();
    _analyticsKey.currentState?.refresh();
    _historyKey.currentState?.refresh();

    // Revenir sur le dashboard
    setState(() {
      _currentIndex = 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: [
          DashboardScreen(
            key: _dashboardKey,
            session: widget.session,
            onAddExpenseTap: () => setState(() => _currentIndex = 1),
          ),
          AddExpenseScreen(
            onExpenseAdded: _onExpenseAdded,
          ),
          AnalyticsScreen(
            key: _analyticsKey,
          ),
          ExpenseHistoryScreen(
            key: _historyKey,
          ),
        ],
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: 10,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (index) {
            setState(() => _currentIndex = index);
            if (index == 0) _dashboardKey.currentState?.refresh();
            if (index == 2) _analyticsKey.currentState?.refresh();
            if (index == 3) _historyKey.currentState?.refresh();
          },
          selectedItemColor: const Color(0xFF0284C7),
          unselectedItemColor: const Color(0xFF94A3B8),
          selectedLabelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11),
          unselectedLabelStyle: const TextStyle(fontSize: 11),
          type: BottomNavigationBarType.fixed,
          backgroundColor: Colors.white,
          elevation: 0,
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.dashboard_rounded),
              label: 'Tableau de bord',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.add_circle_rounded, size: 28),
              label: 'Nouvelle Sortie',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.bar_chart_rounded),
              label: 'Statistiques',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.receipt_long_rounded),
              label: 'Historique',
            ),
          ],
        ),
      ),
    );
  }
}
