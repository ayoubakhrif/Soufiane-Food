import sys

# 1. Fix agent_exits_list_screen.dart
with open("lib/screens/agent_exits_list_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace("Future<void> _confirmExit(Map<String, dynamic> exit) async {", "Future<void> _confirmExit(dynamic exit) async {")
with open("lib/screens/agent_exits_list_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)

# 2. Fix exits_history_screen.dart
with open("lib/screens/exits_history_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()
func = """
  Future<void> _deliverExit(int exitId) async {
    try {
      await ApiService.deliverExit(exitId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Sortie marquée comme livrée')));
      _loadExits();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    }
  }
"""
if "_deliverExit" not in content[:content.find("Widget build")]:
    content = content.replace("  @override\n  void initState() {", func + "\n  @override\n  void initState() {")
with open("lib/screens/exits_history_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)

# 3. Fix api_service.dart
with open("lib/services/api_service.dart", "r", encoding="utf-8") as f:
    content = f.read()

new_methods = """
  static Future<Map<String, dynamic>> deliverExit(int exitId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/casa/exit/deliver'),
      headers: _headers,
      body: jsonEncode({'exit_id': exitId}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to deliver exit');
  }

  static Future<Map<String, dynamic>> bulkConfirmExit(List<int> exitIds, int driverId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/casa/exit/bulk_confirm'),
      headers: _headers,
      body: jsonEncode({'exit_ids': exitIds, 'driver_id': driverId}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to bulk confirm exit');
  }
"""
if "deliverExit" not in content:
    content = content.replace("static Future<void> confirmExit(int exitId, int driverId) async {", new_methods + "\n  static Future<void> confirmExit(int exitId, int driverId, {double? qty}) async {")
    content = content.replace("body: jsonEncode({'exit_id': exitId, 'driver_id': driverId}));", "body: jsonEncode({'exit_id': exitId, 'driver_id': driverId, if (qty != null) 'qty': qty}));")

with open("lib/services/api_service.dart", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed all frontend errors!")
