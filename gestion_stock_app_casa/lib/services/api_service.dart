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
    final uri = Uri.parse('$baseUrl/api/stock_casa_field/login');
    final response = await http.post(
      uri,
      headers: _headers,
      body: jsonEncode({'phone': phone, 'password': password}),
    );

    if (response.body.isEmpty) {
      throw Exception('Réponse vide du serveur ()');
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
    final uri = Uri.parse('$baseUrl/api/stock_casa_field/bootstrap');
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

      return {
        'products': products,
        'clients': clients,
        'garages': garages,
      };
    } else {
      throw Exception(data['message'] ?? 'Impossible de charger les données');
    }
  }

  static Future<List<StockCard>> fetchStock() async {
    final uri = Uri.parse('$baseUrl/api/stock_casa_field/stock');
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

  static Future<Map<String, dynamic>> createEntry(Map<String, dynamic> payload) async {
    final uri = Uri.parse('$baseUrl/api/stock_casa_field/entry');
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
        'message': 'Pas de connexion réseau. Enregistré localement pour synchronisation !'
      };
    }

    try {
      final data = jsonDecode(response.body);
      if (response.statusCode == 200 && data['status'] == 'success') {
        return data;
      } else {
        return {
          'status': 'error',
          'message': data['message'] ?? 'Erreur lors de l\'enregistrement de l\'entrée (Code: ${response.statusCode})'
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
    final uri = Uri.parse('$baseUrl/api/stock_casa_field/exit');
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
        'message': 'Pas de connexion réseau. Enregistré localement pour synchronisation !'
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
    final uri = Uri.parse('$baseUrl/api/stock_casa_field/transfer');
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
        'message': 'Pas de connexion réseau. Enregistré localement pour synchronisation !'
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
          path = '/api/stock_casa_field/entry';
        } else if (op.type == 'exit') {
          path = '/api/stock_casa_field/exit';
        } else if (op.type == 'transfer') {
          path = '/api/stock_casa_field/transfer';
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
}
