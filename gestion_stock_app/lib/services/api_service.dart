import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/agent.dart';
import '../models/item_models.dart';
import '../models/stock_card.dart';
import '../models/pending_operation.dart';
import 'local_storage_service.dart';

class ApiService {
  static const String baseUrl = 'https://gestia-soufianefoods.cloud';

  static Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  static Future<Agent> login(String phone, String password) async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/login');
    final response = await http.post(
      uri,
      headers: _headers,
      body: jsonEncode({'phone': phone, 'password': password}),
    );

    if (response.body.isEmpty) {
      throw Exception('RÃ©ponse vide du serveur ()');
    }

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      final agent = Agent.fromJson(data['agent']);
      await LocalStorageService.saveAgentSession(agent);
      return agent;
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de la connexion');
    }
  }

  static Future<Map<String, dynamic>> fetchBootstrap() async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/bootstrap');
    final response = await http.get(uri, headers: _headers);

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      final products = (data['products'] as List)
          .map((p) => ProductItem.fromJson(p))
          .toList();
      final clients = (data['clients'] as List)
          .map((c) => ClientItem.fromJson(c))
          .toList();
      final garages = (data['garages'] as List)
          .map((g) => GarageItem.fromJson(g))
          .toList();
      final drivers = data['drivers'] != null ? (data['drivers'] as List)
          .map((d) => DriverItem.fromJson(d))
          .toList() : <DriverItem>[];

      return {
        'products': products,
        'clients': clients,
        'garages': garages,
        'drivers': drivers,
      };
    } else {
      throw Exception(data['message'] ?? 'Impossible de charger les donnÃ©es');
    }
  }

  static Future<List<StockCard>> fetchStock() async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/stock');
    final response = await http.get(uri, headers: _headers);

    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return (data['stock'] as List)
          .map((item) => StockCard.fromJson(item))
          .toList();
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de la rÃ©cupÃ©ration du stock');
    }
  }

  static Future<Map<String, dynamic>> createEntry(Map<String, dynamic> payload) async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/entry');
    http.Response response;
    try {
      response = await http.post(
        uri,
        headers: _headers,
        body: jsonEncode(payload),
      );
    } catch (e) {
      await LocalStorageService.savePendingOperation(
        PendingOperation(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          type: 'entry',
          data: payload,
          createdAt: DateTime.now(),
        ),
      );
      return {
        'status': 'offline',
        'message': 'Pas de connexion rÃ©seau. EnregistrÃ© localement pour synchronisation !'
      };
    }

    try {
      final data = jsonDecode(response.body);
      if (response.statusCode == 200 && data['status'] == 'success') {
        return data;
      } else {
        return {
          'status': 'error',
          'message': data['message'] ?? 'Erreur lors de l\'enregistrement de l\'entrÃ©e (Code: ${response.statusCode})'
        };
      }
    } catch (_) {
      return {
        'status': 'error',
        'message': 'Erreur serveur (${response.statusCode}): ${response.body}'
      };
    }
  }

  static Future<Map<String, dynamic>> createExit(Map<String, dynamic> payload) async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/exit');
    http.Response response;
    try {
      response = await http.post(
        uri,
        headers: _headers,
        body: jsonEncode(payload),
      );
    } catch (e) {
      await LocalStorageService.savePendingOperation(
        PendingOperation(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          type: 'exit',
          data: payload,
          createdAt: DateTime.now(),
        ),
      );
      return {
        'status': 'offline',
        'message': 'Pas de connexion rÃ©seau. EnregistrÃ© localement pour synchronisation !'
      };
    }

    try {
      final data = jsonDecode(response.body);
      if (response.statusCode == 200 && data['status'] == 'success') {
        return data;
      } else {
        return {
          'status': 'error',
          'message': data['message'] ?? 'Erreur lors de l\'enregistrement de la sortie (Code: ${response.statusCode})'
        };
      }
    } catch (_) {
      return {
        'status': 'error',
        'message': 'Erreur serveur (${response.statusCode}): ${response.body}'
      };
    }
  }

  static Future<Map<String, dynamic>> createTransfer(Map<String, dynamic> payload) async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/transfer');
    http.Response response;
    try {
      response = await http.post(
        uri,
        headers: _headers,
        body: jsonEncode(payload),
      );
    } catch (e) {
      await LocalStorageService.savePendingOperation(
        PendingOperation(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          type: 'transfer',
          data: payload,
          createdAt: DateTime.now(),
        ),
      );
      return {
        'status': 'offline',
        'message': 'Pas de connexion rÃ©seau. EnregistrÃ© localement pour synchronisation !'
      };
    }

    try {
      final data = jsonDecode(response.body);
      if (response.statusCode == 200 && data['status'] == 'success') {
        return data;
      } else {
        return {
          'status': 'error',
          'message': data['message'] ?? 'Erreur lors du transfert (Code: ${response.statusCode})'
        };
      }
    } catch (_) {
      return {
        'status': 'error',
        'message': 'Erreur serveur (${response.statusCode}): ${response.body}'
      };
    }
  }

  static Future<int> syncPendingOperations() async {
    final pending = await LocalStorageService.getPendingOperations();
    int syncedCount = 0;

    for (final op in pending) {
      try {
        final Map<String, dynamic> data = Map<String, dynamic>.from(op.data);
        if (data['date'] == '--' || data['date'] == null || data['date'].toString().isEmpty) {
          data['date'] = DateTime.now().toIso8601String().split('T')[0];
        }

        String path;
        if (op.type == 'entry') {
          path = '/api/kal3iya/entry';
        } else if (op.type == 'exit') {
          path = '/api/kal3iya/exit';
        } else if (op.type == 'transfer') {
          path = '/api/kal3iya/transfer';
        } else {
          continue;
        }

        final res = await http.post(
          Uri.parse('$baseUrl$path'),
          headers: _headers,
          body: jsonEncode(data),
        );
        if (res.statusCode == 200) {
          final resData = jsonDecode(res.body);
          if (resData['status'] == 'success') {
            await LocalStorageService.removePendingOperation(op.id);
            syncedCount++;
          }
        }
      } catch (e) {
        debugPrint('Erreur synchronisation: $e');
        break;
      }
    }
    return syncedCount;
  }


  static Future<Map<String, dynamic>> createBulkExit(Map<String, dynamic> payload) async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/bulk_exit');
    final response = await http.post(uri, headers: _headers, body: jsonEncode(payload));
    return jsonDecode(response.body);
  }

  static Future<List<Map<String, dynamic>>> fetchDriverExits(int driverId) async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/driver_exits');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'driver_id': driverId}));
    final data = jsonDecode(response.body);
    if (data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['exits']);
    } else {
      throw Exception(data['message'] ?? 'Erreur');
    }
  }

  static Future<Map<String, dynamic>> markDelivered(List<int> exitIds) async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/mark_delivered');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'exit_ids': exitIds}));
    return jsonDecode(response.body);
  }

  static Future<List<Map<String, dynamic>>> fetchExits() async {

    final uri = Uri.parse('$baseUrl/api/kal3iya/exits');
    final response = await http.get(uri, headers: _headers);
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['exits']);
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de la rÃ©cupÃ©ration des sorties');
    }
  }

  static Future<Map<String, dynamic>> createReturn(Map<String, dynamic> payload) async {
    final uri = Uri.parse('$baseUrl/api/kal3iya/return');
    http.Response response;
    try {
      response = await http.post(
        uri,
        headers: _headers,
        body: jsonEncode(payload),
      );
    } catch (e) {
      throw Exception('Erreur rÃ©seau. Impossible de contacter le serveur.');
    }

    try {
      final data = jsonDecode(response.body);
      if (response.statusCode == 200 && data['status'] == 'success') {
        return data;
      } else {
        return {
          'status': 'error',
          'message': data['message'] ?? 'Erreur (Code: ${response.statusCode})'
        };
      }
    } catch (_) {
      return {
        'status': 'error',
        'message': 'Erreur serveur (${response.statusCode}): ${response.body}'
      };
    }
  }
}


