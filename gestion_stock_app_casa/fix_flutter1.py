import os

with open("lib/services/api_service.dart", "r", encoding="utf-8") as f:
    content = f.read()

new_method = """  static Future<void> confirmExit(int exitId) async {
    final uri = Uri.parse('$baseUrl/api/casa/exit/confirm');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'exit_id': exitId}));
    final data = jsonDecode(response.body);
    if (response.statusCode != 200 || data['status'] != 'success') {
      throw Exception(data['message'] ?? 'Erreur de confirmation');
    }
  }"""

content = content.replace(
    "static Future<List<Map<String, dynamic>>> fetchCommercialOrders(int agentId) async {",
    new_method + "\n\n  static Future<List<Map<String, dynamic>>> fetchCommercialOrders(int agentId) async {"
)
with open("lib/services/api_service.dart", "w", encoding="utf-8") as f:
    f.write(content)


with open("lib/screens/home_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("import 'stock_exit_screen.dart';", "import 'stock_exit_screen.dart';\nimport 'agent_exits_list_screen.dart';")
content = content.replace(
    "Navigator.push(context, MaterialPageRoute(builder: (_) => StockExitScreen(agent: widget.agent)))",
    "Navigator.push(context, MaterialPageRoute(builder: (_) => AgentExitsListScreen(agent: widget.agent)))"
)
content = content.replace("'Créer Sortie (Bl)'", "'Historique Sorties'")

with open("lib/screens/home_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)


with open("lib/screens/stock_exit_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("'Confirmer la tournée'", "'Enregistrer'")
content = content.replace("L'état de la tournée a été mise à jour.", "Tournée enregistrée avec succès.")
content = content.replace("Tournée enregistrée avec succès avec succès.", "Tournée enregistrée avec succès.")

with open("lib/screens/stock_exit_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
    
with open("lib/screens/exits_history_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()
    
content = content.replace(
    "if (state == 'done') return 'Confirmé';",
    "if (state == 'done') return 'Confirmé';\n    if (state == 'registered') return 'Enregistré';"
)
content = content.replace(
    "bool allDelivered = items.every((i) => i['state'] == 'delivered');\n                      String groupState = allDelivered ? 'Livré' : 'Confirmé';\n                      Color groupColor = allDelivered ? Colors.green : Colors.orange;",
    "bool allDelivered = items.every((i) => i['state'] == 'delivered');\n                      bool anyRegistered = items.any((i) => i['state'] == 'registered');\n                      String groupState = allDelivered ? 'Livré' : (anyRegistered ? 'Enregistré' : 'Confirmé');\n                      Color groupColor = allDelivered ? Colors.green : (anyRegistered ? Colors.blue : Colors.orange);"
)

with open("lib/screens/exits_history_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated basic screens")
