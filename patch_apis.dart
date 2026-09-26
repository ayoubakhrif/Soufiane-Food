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
