import sys

with open("lib/screens/agent_exits_list_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Replace _confirmExit(int exitId) with _confirmExit(Map<String, dynamic> exit)
old_func = """Future<void> _confirmExit(int exitId) async {
    DriverItem? selectedDriver;
    final bool? result = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setStateSB) {
            return AlertDialog(
              title: const Text('Confirmer le dÃ©part'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Veuillez sÃ©lectionner le chauffeur pour cette sortie :'),
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
                      ScaffoldMessenger.of(ctx).showSnackBar(const SnackBar(content: Text('Veuillez sÃ©lectionner un chauffeur')));
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
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Sortie confirmÃ©e avec succÃ¨s.')));
        _loadExits();
      } catch (e) {
        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }"""

new_func = """Future<void> _confirmExit(Map<String, dynamic> exit) async {
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
  }"""

content = content.replace(old_func, new_func)
content = content.replace("onPressed: () => _confirmExit(exit['id']),", "onPressed: () => _confirmExit(exit),")

with open("lib/screens/agent_exits_list_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated agent exits list screen")
