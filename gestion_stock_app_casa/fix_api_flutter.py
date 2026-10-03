# -*- coding: utf-8 -*-
import sys

with open("lib/services/api_service.dart", "r", encoding="utf-8") as f:
    content = f.read()

old_fetch_exits = """  static Future<List<Map<String, dynamic>>> fetchExits() async {
    final uri = Uri.parse('$baseUrl/api/casa/exits');
    final response = await http.get(uri, headers: _headers);
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['exits']);
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de la récupération des sorties');
    }
  }"""

new_fetch_exits = """  static Future<List<Map<String, dynamic>>> fetchExits() async {
    final uri = Uri.parse('$baseUrl/api/casa/commercial/exits_history');
    final response = await http.get(uri, headers: _headers);
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['exits']);
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de la récupération des sorties');
    }
  }

  static Future<List<Map<String, dynamic>>> fetchCommercialOrders(int agentId) async {
    final uri = Uri.parse('$baseUrl/api/casa/commercial/orders_history');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'commercial_id': agentId}));
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['orders']);
    } else {
      throw Exception(data['message'] ?? 'Erreur');
    }
  }"""

content = content.replace(old_fetch_exits, new_fetch_exits)

with open("lib/services/api_service.dart", "w", encoding="utf-8") as f:
    f.write(content)

print("Done api")
