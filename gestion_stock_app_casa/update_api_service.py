import sys

with open("lib/services/api_service.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Add deliverExit and bulkConfirmExit
new_methods = """
  static Future<Map<String, dynamic>> deliverExit(int exitId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/exit/deliver'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'exit_id': exitId}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to deliver exit');
  }

  static Future<Map<String, dynamic>> bulkConfirmExit(List<int> exitIds, int driverId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/exit/bulk_confirm'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'exit_ids': exitIds, 'driver_id': driverId}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to bulk confirm exit');
  }
"""

content = content.replace("static Future<Map<String, dynamic>> confirmExit(int exitId, int driverId) async {", new_methods + "\n  static Future<Map<String, dynamic>> confirmExit(int exitId, int driverId, {double? qty}) async {")

content = content.replace("body: jsonEncode({'exit_id': exitId, 'driver_id': driverId}),", "body: jsonEncode({'exit_id': exitId, 'driver_id': driverId, if (qty != null) 'qty': qty}),")

with open("lib/services/api_service.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated ApiService")
