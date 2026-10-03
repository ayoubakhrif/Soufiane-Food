import sys

with open("lib/screens/exits_history_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Add deliverExit function inside class
func = """
  Future<void> _deliverExit(int exitId) async {
    try {
      await ApiService.deliverExit(exitId);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Sortie marquée comme livrée')));
      _fetchHistory();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    }
  }
"""
content = content.replace("void _filterHistory(String query) {", func + "\n  void _filterHistory(String query) {")

# Add button
btn = """
                                    if (item['state'] == 'done')
                                      Align(
                                        alignment: Alignment.centerRight,
                                        child: ElevatedButton(
                                          onPressed: () => _deliverExit(item['id']),
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor: Colors.green,
                                            foregroundColor: Colors.white,
                                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                            minimumSize: Size.zero,
                                          ),
                                          child: const Text('Marquer Livré', style: TextStyle(fontSize: 12)),
                                        ),
                                      ),
"""

content = content.replace("const SizedBox(height: 8),", "const SizedBox(height: 8),\n" + btn, 1)

with open("lib/screens/exits_history_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated exits history screen")
