
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/item_models.dart';
import '../models/stock_card.dart';

class ApiService {
  static const String baseUrl = 'https://gestia-soufianefoods.cloud';
  static const Map<String, String> _headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  static Future<Map<String, dynamic>> login(String phone, String password) async {
    final uri = Uri.parse('\/api/casa/login');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'phone': phone, 'password': password}));
    return jsonDecode(response.body);
  }

  static Future<Map<String, dynamic>> fetchBootstrap() async {
    final uri = Uri.parse('\/api/casa/bootstrap');
    final response = await http.get(uri, headers: _headers);

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      final products = (data['products'] as List)
          .map((p) => ProductItem.fromJson(p))
          .toList();
      final clients = (data['clients'] as List)
          .map((c) => ClientItem.fromJson(c))
          .toList();
      return {'products': products, 'clients': clients};
    } else {
      throw Exception(data['message'] ?? 'Erreur lors du chargement des données');
    }
  }

  static Future<List<StockCard>> fetchStock() async {
    final uri = Uri.parse('\/api/casa/stock');
    final response = await http.get(uri, headers: _headers);

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return (data['stock'] as List)
          .map((item) => StockCard.fromJson(item))
          .toList();
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de la récupération du stock');
    }
  }

  static Future<Map<String, dynamic>> bulkExit(Map<String, dynamic> payload) async {
    final uri = Uri.parse('\/api/casa/bulk_exit');
    final response = await http.post(uri, headers: _headers, body: jsonEncode(payload));
    return jsonDecode(response.body);
  }

  static Future<List<Map<String, dynamic>>> fetchExits() async {
    final uri = Uri.parse('\/api/casa/commercial/exits_history');
    final response = await http.get(uri, headers: _headers);
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['exits']);
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de la récupération des sorties');
    }
  }

  static Future<List<Map<String, dynamic>>> fetchCommercialOrders(int agentId) async {
    final uri = Uri.parse('\/api/casa/commercial/orders_history');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'commercial_id': agentId}));
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['orders']);
    } else {
      throw Exception(data['message'] ?? 'Erreur');
    }
  }

  static Future<Map<String, dynamic>> submitReturn(Map<String, dynamic> payload) async {
    final uri = Uri.parse('\/api/casa/return');
    final response = await http.post(uri, headers: _headers, body: jsonEncode(payload));
    return jsonDecode(response.body);
  }

  static Future<List<Map<String, dynamic>>> fetchDriverExits(int driverId) async {
    final uri = Uri.parse('\/api/casa/driver_exits');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'driver_id': driverId}));
    final data = jsonDecode(response.body);
    if (data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['exits']);
    } else {
      throw Exception(data['message'] ?? 'Erreur');
    }
  }

  static Future<Map<String, dynamic>> markDelivered(List<int> exitIds) async {
    final uri = Uri.parse('\/api/casa/driver_deliver');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'exit_ids': exitIds}));
    return jsonDecode(response.body);
  }

  static Future<int> fetchPendingOrdersCount() async {
    final uri = Uri.parse('\/api/casa/orders/pending_count');
    final response = await http.get(uri, headers: _headers);
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return data['count'] as int;
    }
    return 0;
  }

  static Future<List<dynamic>> fetchPendingOrders() async {
    final uri = Uri.parse('\/api/casa/orders');
    final response = await http.get(uri, headers: _headers);
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return data['orders'] as List;
    }
    throw Exception('Erreur de chargement des commandes');
  }

  static Future<Map<String, dynamic>> createOrder(Map<String, dynamic> payload) async {
    final uri = Uri.parse('\/api/casa/orders/create');
    final response = await http.post(uri, headers: _headers, body: jsonEncode(payload));
    return jsonDecode(response.body);
  }

  static Future<void> validateOrder(int orderId) async {
    final uri = Uri.parse('\/api/casa/orders/validate');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'order_id': orderId}));
    final data = jsonDecode(response.body);
    if (data['status'] != 'success') {
      throw Exception(data['message'] ?? 'Erreur lors de la validation');
    }
  }
}
