import sys

with open("lib/services/api_service.dart", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "static Future<void> confirmExit(int exitId) async {\n    final uri = Uri.parse('$baseUrl/api/casa/exit/confirm');\n    final response = await http.post(uri, headers: _headers, body: jsonEncode({'exit_id': exitId}));",
    "static Future<void> confirmExit(int exitId, int driverId) async {\n    final uri = Uri.parse('$baseUrl/api/casa/exit/confirm');\n    final response = await http.post(uri, headers: _headers, body: jsonEncode({'exit_id': exitId, 'driver_id': driverId}));"
)

with open("lib/services/api_service.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated api_service.dart")
