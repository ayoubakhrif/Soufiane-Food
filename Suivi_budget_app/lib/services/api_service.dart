import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/user_session.dart';
import '../models/dashboard_data.dart';
import '../models/category_model.dart';
import '../models/expense_model.dart';
import '../models/analytics_data.dart';
import 'storage_service.dart';

class ApiService {
  static Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  static Future<String> _getBaseUrl() async {
    return await StorageService.getServerUrl();
  }

  // =========================================================================
  // 🔑 AUTHENTICATION
  // =========================================================================
  static Future<UserSession> login(String login, String password) async {
    final baseUrl = await _getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/suivi/login');

    final response = await http.post(
      uri,
      headers: _headers,
      body: jsonEncode({
        'login': login,
        'password': password,
      }),
    );

    if (response.body.isEmpty) {
      throw Exception('Réponse vide du serveur');
    }

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      final user = data['user'];
      final session = UserSession(
        id: user['id'],
        name: user['name'] ?? login,
        login: user['login'] ?? login,
        serverUrl: baseUrl,
      );
      await StorageService.saveSession(session);
      return session;
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de la connexion');
    }
  }

  // =========================================================================
  // 📊 DASHBOARD
  // =========================================================================
  static Future<DashboardData> fetchDashboard() async {
    final baseUrl = await _getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/suivi/dashboard');

    final response = await http.get(uri, headers: _headers);
    if (response.body.isEmpty) {
      throw Exception('Réponse vide du serveur');
    }

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return DashboardData.fromJson(data['data']);
    } else {
      throw Exception(data['message'] ?? 'Impossible de charger le tableau de bord');
    }
  }

  // =========================================================================
  // 📑 CATEGORIES
  // =========================================================================
  static Future<List<CategoryModel>> fetchCategories() async {
    final baseUrl = await _getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/suivi/categories');

    final response = await http.get(uri, headers: _headers);
    if (response.body.isEmpty) {
      throw Exception('Réponse vide du serveur');
    }

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      final list = data['data'] as List<dynamic>? ?? [];
      return list.map((c) => CategoryModel.fromJson(c as Map<String, dynamic>)).toList();
    } else {
      throw Exception(data['message'] ?? 'Impossible de charger les catégories');
    }
  }

  // =========================================================================
  // ➕ CREATE EXPENSE (QUOTIDIENNE OU MENSUELLE FIXE)
  // =========================================================================
  static Future<Map<String, dynamic>> createExpense({
    required double amount,
    int? categoryId,
    String? categoryName,
    String? date,
    String? description,
    String? receiptBase64,
    String? receiptFilename,
    bool isMonthly = false,
  }) async {
    final baseUrl = await _getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/suivi/expense/create');

    final payload = {
      'amount': amount,
      'is_monthly': isMonthly,
      if (categoryId != null) 'category_id': categoryId,
      if (categoryName != null) 'category_name': categoryName,
      if (date != null) 'date': date,
      'description': description ?? '',
      if (receiptBase64 != null) 'receipt_image': receiptBase64,
      if (receiptFilename != null) 'receipt_filename': receiptFilename,
    };

    final response = await http.post(
      uri,
      headers: _headers,
      body: jsonEncode(payload),
    );

    if (response.body.isEmpty) {
      throw Exception('Réponse vide du serveur');
    }

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return data;
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de l\'enregistrement de la dépense');
    }
  }

  // =========================================================================
  // 🗑️ DELETE MONTHLY EXPENSE
  // =========================================================================
  static Future<void> deleteMonthlyExpense(int id) async {
    final baseUrl = await _getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/suivi/monthly_expense/delete/$id');

    final response = await http.post(uri, headers: _headers);
    final data = jsonDecode(response.body);
    if (response.statusCode != 200 || data['status'] != 'success') {
      throw Exception(data['message'] ?? 'Impossible de supprimer la charge');
    }
  }

  // =========================================================================
  // 📜 EXPENSES HISTORY
  // =========================================================================
  static Future<List<ExpenseModel>> fetchExpenses({
    int? categoryId,
    int limit = 60,
    bool allPeriod = false,
  }) async {
    final baseUrl = await _getBaseUrl();
    String query = '?limit=$limit';
    if (categoryId != null) query += '&category_id=$categoryId';
    if (allPeriod) query += '&all_period=1';

    final uri = Uri.parse('$baseUrl/api/suivi/expenses$query');
    final response = await http.get(uri, headers: _headers);

    if (response.body.isEmpty) {
      throw Exception('Réponse vide du serveur');
    }

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      final list = data['data'] as List<dynamic>? ?? [];
      return list.map((e) => ExpenseModel.fromJson(e as Map<String, dynamic>)).toList();
    } else {
      throw Exception(data['message'] ?? 'Impossible de charger l\'historique');
    }
  }

  // =========================================================================
  // 🖼️ RECEIPT IMAGE URL
  // =========================================================================
  static Future<String> getReceiptImageUrl(int expenseId) async {
    final baseUrl = await _getBaseUrl();
    return '$baseUrl/api/suivi/receipt/$expenseId';
  }

  // =========================================================================
  // 📊 ANALYTICS & STATS
  // =========================================================================
  static Future<AnalyticsData> fetchAnalytics() async {
    final baseUrl = await _getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/suivi/analytics');

    final response = await http.get(uri, headers: _headers);

    if (response.body.isEmpty) {
      throw Exception('Réponse vide du serveur');
    }

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return AnalyticsData.fromJson(data['data']);
    } else {
      throw Exception(data['message'] ?? 'Impossible de charger les statistiques');
    }
  }
}
