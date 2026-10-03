import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'package:collection/collection.dart';

class ExitsHistoryScreen extends StatefulWidget {
  const ExitsHistoryScreen({super.key});
  @override
  State<ExitsHistoryScreen> createState() => _ExitsHistoryScreenState();
}

class _ExitsHistoryScreenState extends State<ExitsHistoryScreen> {
  bool _isLoading = true;
  List<Map<String, dynamic>> _exits = [];
  Map<String, List<Map<String, dynamic>>> _groupedExits = {};

  @override
  void initState() {
    super.initState();
    _loadExits();
  }

  Future<void> _loadExits() async {
    setState(() => _isLoading = true);
    try {
      final exits = await ApiService.fetchExits();
      if (!mounted) return;
      setState(() {
        _exits = exits;
        
        // Group by Client Name + Date (day only)
        _groupedExits = groupBy(_exits, (Map<String, dynamic> e) {
          final dateDay = e['date'].toString().split(' ')[0];
          final client = e['client_name']?.toString().isEmpty ?? true ? 'Client Inconnu' : e['client_name'];
          return '${client}|${dateDay}';
        });
        
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }
  
  Color _getStateColor(String state) {
    if (state == 'delivered') return Colors.green;
    if (state == 'done') return Colors.orange;
    return Colors.grey;
  }
  
  String _getStateText(String state) {
    if (state == 'delivered') return 'Livré';
    if (state == 'done') return 'Confirmé';
    if (state == 'registered') return 'Enregistré';
    return state;
  }

  void _showGroupDetails(String key, List<Map<String, dynamic>> items) {
    final parts = key.split('|');
    final clientName = parts[0];
    final dateDay = parts.length > 1 ? parts[1] : '';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.only(topLeft: Radius.circular(20), topRight: Radius.circular(20)),
          ),
          padding: const EdgeInsets.all(20),
          height: MediaQuery.of(context).size.height * 0.85,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Sorties : ${clientName}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              Text('Date : ${dateDay}', style: const TextStyle(fontSize: 16, color: Colors.grey)),
              const SizedBox(height: 16),
              Expanded(
                child: ListView.builder(
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final item = items[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 80,
                              height: 80,
                              decoration: BoxDecoration(
                                color: Colors.grey.shade200,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: item['image_url'] != null && item['image_url'].toString().isNotEmpty
                                  ? ClipRRect(
                                      borderRadius: BorderRadius.circular(8),
                                      child: Image.network(item['image_url'], fit: BoxFit.cover,
                                        errorBuilder: (c, e, s) => const Icon(Icons.image_not_supported, color: Colors.grey),
                                      ),
                                    )
                                  : const Icon(Icons.inventory_2, color: Colors.grey, size: 40),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(item['product_name'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                                  const SizedBox(height: 4),
                                  Text('Qté: ${item['qty']} | Tonnage: ${item['tonnage']} Kg', style: const TextStyle(color: Colors.black87)),
                                  Text('Chauffeur: ${item['driver_name']}', style: const TextStyle(color: Colors.black54, fontSize: 12)),
                                  const SizedBox(height: 8),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: _getStateColor(item['state']).withOpacity(0.1),
                                      borderRadius: BorderRadius.circular(12),
                                      border: Border.all(color: _getStateColor(item['state'])),
                                    ),
                                    child: Text(_getStateText(item['state']), style: TextStyle(color: _getStateColor(item['state']), fontSize: 12, fontWeight: FontWeight.bold)),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final keys = _groupedExits.keys.toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Historique des Sorties'),
        backgroundColor: Colors.blue.shade900,
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _groupedExits.isEmpty
              ? const Center(child: Text('Aucune sortie trouvée'))
              : RefreshIndicator(
                  onRefresh: _loadExits,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: keys.length,
                    itemBuilder: (context, index) {
                      final key = keys[index];
                      final items = _groupedExits[key]!;
                      final parts = key.split('|');
                      final clientName = parts[0];
                      final dateDay = parts.length > 1 ? parts[1] : '';
                      
                      bool allDelivered = items.every((i) => i['state'] == 'delivered');
                      bool anyRegistered = items.any((i) => i['state'] == 'registered');
                      String groupState = allDelivered ? 'Livré' : (anyRegistered ? 'Enregistré' : 'Confirmé');
                      Color groupColor = allDelivered ? Colors.green : (anyRegistered ? Colors.blue : Colors.orange);

                      return Card(
                        elevation: 3,
                        margin: const EdgeInsets.only(bottom: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        child: ListTile(
                          contentPadding: const EdgeInsets.all(16),
                          leading: CircleAvatar(
                            backgroundColor: Colors.blue.shade100,
                            child: const Icon(Icons.local_shipping, color: Colors.blue),
                          ),
                          title: Text(clientName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                          subtitle: Text('${dateDay} • ${items.length} produit(s)'),
                          trailing: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: groupColor.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: groupColor),
                            ),
                            child: Text(groupState, style: TextStyle(color: groupColor, fontWeight: FontWeight.bold, fontSize: 12)),
                          ),
                          onTap: () => _showGroupDetails(key, items),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
