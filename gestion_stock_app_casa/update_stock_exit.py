import sys
import re

with open("lib/screens/stock_exit_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Variables
content = content.replace("List<StockCard> _allStock = [];", "List<StockCard> _allStock = [];\n  bool _isRegistered = false;\n  List<int> _registeredExitIds = [];\n  DriverItem? _selectedDriver;")

# _submit
old_submit = """      try {
      final res = await ApiService.createBulkExit({
        'driver_id': 0,
        'order_reference': orderRef,
        'lines': parsedLines,
      });
      if (!mounted) return;
      if (res['status'] == 'success') {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['message'])));
        Navigator.pop(context);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['message'] ?? 'Erreur inconnue')));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }"""

new_submit = """      try {
      final res = await ApiService.createBulkExit({
        'driver_id': 0,
        'order_reference': orderRef,
        'lines': parsedLines,
      });
      if (!mounted) return;
      if (res['status'] == 'success') {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['message'])));
        setState(() {
          _isRegistered = true;
          _registeredExitIds = List<int>.from(res['exit_ids'] ?? []);
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['message'] ?? 'Erreur inconnue')));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }"""
content = content.replace(old_submit, new_submit)

# Valider la tournée function
func = """
  Future<void> _validerTournee() async {
    if (_selectedDriver == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez sélectionner un chauffeur')));
      return;
    }
    setState(() => _isLoading = true);
    try {
      await ApiService.bulkConfirmExit(_registeredExitIds, _selectedDriver!.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Tournée validée avec succès !')));
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }
"""
content = content.replace("void _submit() async {", func + "\n  void _submit() async {")

# UI bottom bar
old_bottom = """      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: ElevatedButton(
            onPressed: _isLoading ? null : _submit,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.purple.shade800,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: _isLoading
                ? const CircularProgressIndicator(color: Colors.white)
                : const Text('Enregistrer', style: TextStyle(fontSize: 18, color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ),
      ),"""

new_bottom = """      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: _isRegistered ? 
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<DriverItem>(
                value: _selectedDriver,
                decoration: const InputDecoration(labelText: 'Chauffeur', border: OutlineInputBorder()),
                items: _drivers.map((d) => DropdownMenuItem(value: d, child: Text(d.name))).toList(),
                onChanged: (val) => setState(() => _selectedDriver = val),
              ),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: _isLoading ? null : _validerTournee,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  minimumSize: const Size.infinity,
                ),
                child: _isLoading
                    ? const CircularProgressIndicator(color: Colors.white)
                    : const Text('Valider la tournée', style: TextStyle(fontSize: 18, color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ],
          )
          : ElevatedButton(
            onPressed: _isLoading ? null : _submit,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.purple.shade800,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              minimumSize: const Size.infinity,
            ),
            child: _isLoading
                ? const CircularProgressIndicator(color: Colors.white)
                : const Text('Enregistrer', style: TextStyle(fontSize: 18, color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ),
      ),"""
content = content.replace(old_bottom, new_bottom)

with open("lib/screens/stock_exit_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated stock_exit_screen.dart")
