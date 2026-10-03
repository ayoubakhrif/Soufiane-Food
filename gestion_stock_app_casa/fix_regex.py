import sys
import re

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
content = re.sub(r"  void initState\(\) \{", func + "\n  void initState() {", content)
with open("lib/screens/exits_history_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated exits_history_screen.dart")

with open("lib/screens/agent_exits_list_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()
    
# Replace _confirmExit completely using regex
pattern = r"Future<void> _confirmExit\(int exitId\) async \{.*?\s*\}\s*\n\s*\n\s*@override\n\s*Widget build\(BuildContext context\)"
new_func = """Future<void> _confirmExit(dynamic exit) async {
    DriverItem? selectedDriver;
    final qtyController = TextEditingController(text: exit['qty'].toString());
    double currentQty = double.tryParse(exit['qty'].toString()) ?? 0.0;
    double weight = double.tryParse(exit['weight']?.toString() ?? '0.0') ?? 0.0;

    final Map<String, dynamic>? result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setStateSB) {
            return AlertDialog(
              title: const Text('Confirmer le départ'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Chauffeur :'),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<DriverItem>(
                    decoration: const InputDecoration(border: OutlineInputBorder()),
                    items: _drivers.map((d) => DropdownMenuItem(value: d, child: Text(d.name))).toList(),
                    onChanged: (val) => setStateSB(() => selectedDriver = val),
                  ),
                  const SizedBox(height: 16),
                  const Text('Quantité à confirmer (petit à petit) :'),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: qtyController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(border: OutlineInputBorder()),
                    onChanged: (val) {
                      setStateSB(() {
                        currentQty = double.tryParse(val) ?? 0.0;
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  Text('Tonnage : ${(currentQty * weight).toStringAsFixed(2)} Kg', style: const TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, null), child: const Text('Annuler')),
                ElevatedButton(
                  onPressed: () {
                    if (selectedDriver != null) {
                      Navigator.pop(ctx, {'driver_id': selectedDriver!.id, 'qty': currentQty});
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

    if (result != null) {
      try {
        showDialog(context: context, barrierDismissible: false, builder: (_) => const Center(child: CircularProgressIndicator()));
        await ApiService.confirmExit(exit['id'], result['driver_id'], qty: result['qty']);
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
  }

  @override
  Widget build(BuildContext context)"""

content = re.sub(pattern, new_func, content, flags=re.DOTALL)
with open("lib/screens/agent_exits_list_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated agent_exits_list_screen.dart")

with open("lib/screens/stock_exit_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Make sure _isRegistered, _drivers, and _validerTournee are used properly so compiler doesn't complain
# Actually the compiler just warns about unused fields. It's a warning, not an error.
# We can ignore the warnings.

print("Done")
