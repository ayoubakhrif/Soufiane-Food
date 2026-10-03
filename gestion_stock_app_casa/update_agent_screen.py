import sys

with open("lib/screens/agent_exits_list_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Add drivers fetch
content = content.replace("List<Map<String, dynamic>> _exits = [];", "List<Map<String, dynamic>> _exits = [];\n  List<DriverItem> _drivers = [];")
content = content.replace("import '../services/api_service.dart';", "import '../services/api_service.dart';\nimport '../models/driver_item.dart';")

content = content.replace(
    "final list = await ApiService.fetchExits(); // Returns done and registered exits",
    "final list = await ApiService.fetchExits();\n      final drvs = await ApiService.fetchDrivers();"
)
content = content.replace(
    "setState(() {\n        _exits = list;",
    "setState(() {\n        _exits = list;\n        _drivers = drvs;"
)

# Update confirm logic
new_confirm = """  Future<void> _confirmExit(int exitId) async {
    DriverItem? selectedDriver;
    final bool? result = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setStateSB) {
            return AlertDialog(
              title: const Text('Confirmer le départ'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Veuillez sélectionner le chauffeur pour cette sortie :'),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<DriverItem>(
                    decoration: const InputDecoration(labelText: 'Chauffeur', border: OutlineInputBorder()),
                    items: _drivers.map((d) => DropdownMenuItem(value: d, child: Text(d.name))).toList(),
                    onChanged: (val) => setStateSB(() => selectedDriver = val),
                  ),
                ],
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
                ElevatedButton(
                  onPressed: () {
                    if (selectedDriver != null) {
                      Navigator.pop(ctx, true);
                    } else {
                      ScaffoldMessenger.of(ctx).showSnackBar(const SnackBar(content: Text('Veuillez sélectionner un chauffeur')));
                    }
                  },
                  child: const Text('Confirmer'),
                ),
              ],
            );
          }
        );
      }
    );

    if (result == true && selectedDriver != null) {
      try {
        showDialog(context: context, barrierDismissible: false, builder: (_) => const Center(child: CircularProgressIndicator()));
        await ApiService.confirmExit(exitId, selectedDriver!.id);
        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Sortie confirmée avec succès.')));
        _loadExits();
      } catch (e) {
        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }"""

import re
pattern = r"  Future<void> _confirmExit\(int exitId\) async \{.*?\n  \}"
content = re.sub(pattern, new_confirm.strip(), content, flags=re.DOTALL)

with open("lib/screens/agent_exits_list_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated agent_exits_list_screen.dart")
