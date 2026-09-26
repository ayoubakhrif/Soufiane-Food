import codecs

with codecs.open('gestion_stock_app/lib/services/api_service.dart', 'r', encoding='utf-8') as f:
    content = f.read()

new_methods = '''
  static Future<Map<String, dynamic>> createBulkExit(Map<String, dynamic> payload) async {
    final uri = Uri.parse('/api/kal3iya/bulk_exit');
    final response = await http.post(uri, headers: _headers, body: jsonEncode(payload));
    return jsonDecode(response.body);
  }

  static Future<List<Map<String, dynamic>>> fetchDriverExits(int driverId) async {
    final uri = Uri.parse('/api/kal3iya/driver_exits');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'driver_id': driverId}));
    final data = jsonDecode(response.body);
    if (data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['exits']);
    } else {
      throw Exception(data['message'] ?? 'Erreur');
    }
  }

  static Future<Map<String, dynamic>> markDelivered(List<int> exitIds) async {
    final uri = Uri.parse('/api/kal3iya/mark_delivered');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'exit_ids': exitIds}));
    return jsonDecode(response.body);
  }

  static Future<List<Map<String, dynamic>>> fetchExits() async {
'''

content = content.replace("  static Future<List<Map<String, dynamic>>> fetchExits() async {", new_methods)

with codecs.open('gestion_stock_app/lib/services/api_service.dart', 'w', encoding='utf-8') as f:
    f.write(content)
