import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../services/api_service.dart';
import 'stock_exit_screen.dart';
import 'package:collection/collection.dart';

class AgentExitsListScreen extends StatefulWidget {
  final Agent agent;
  const AgentExitsListScreen({super.key, required this.agent});

  @override
  State<AgentExitsListScreen> createState() => _AgentExitsListScreenState();
}

class _AgentExitsListScreenState extends State<AgentExitsListScreen> {
  bool _isLoading = true;
  List<Map<String, dynamic>> _exits = [];

  @override
  void initState() {
    super.initState();
    _loadExits();
  }

  Future<void> _loadExits() async {
    setState(() => _isLoading = true);
    try {
      final list = await ApiService.fetchExits(); // Returns done and registered exits
      if (!mounted) return;
      setState(() {
        _exits = list;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Color _getStateColor(String state) {
    if (state == 'delivered') return Colors.green;
    if (state == 'done') return Colors.orange;
    if (state == 'registered') return Colors.blue;
    return Colors.grey;
  }
  
  String _getStateText(String state) {
    if (state == 'delivered') return 'Livré';
    if (state == 'done') return 'Confirmé';
    if (state == 'registered') return 'Enregistré';
    return state;
  }

  Future<void> _confirmExit(int exitId) async {
    try {
      showDialog(context: context, barrierDismissible: false, builder: (_) => const Center(child: CircularProgressIndicator()));
      await ApiService.confirmExit(exitId);
      if (!mounted) return;
      Navigator.pop(context); // Close loading
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Sortie confirmée et déduite du stock.')));
      _loadExits();
    } catch (e) {
      if (!mounted) return;
      Navigator.pop(context); // Close loading
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Historique des Sorties'),
        backgroundColor: Colors.purple.shade800,
        foregroundColor: Colors.white,
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : _exits.isEmpty 
          ? const Center(child: Text('Aucune sortie trouvée'))
          : RefreshIndicator(
              onRefresh: _loadExits,
              child: ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: _exits.length,
                itemBuilder: (context, index) {
                  final exit = _exits[index];
                  final isRegistered = exit['state'] == 'registered';
                  return Card(
                    elevation: 3,
                    margin: const EdgeInsets.only(bottom: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Text('${exit['name']} - ${exit['client_name']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: _getStateColor(exit['state']).withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: _getStateColor(exit['state'])),
                                ),
                                child: Text(_getStateText(exit['state']), style: TextStyle(color: _getStateColor(exit['state']), fontWeight: FontWeight.bold, fontSize: 12)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text('Produit: ${exit['product_name']} | Qté: ${exit['qty']}'),
                          Text('Date: ${exit['date']}'),
                          
                          if (isRegistered) ...[
                            const SizedBox(height: 12),
                            Align(
                              alignment: Alignment.centerRight,
                              child: ElevatedButton.icon(
                                onPressed: () => _confirmExit(exit['id']),
                                style: ElevatedButton.styleFrom(backgroundColor: Colors.blue.shade700, foregroundColor: Colors.white),
                                icon: const Icon(Icons.check_circle_outline, size: 20),
                                label: const Text('Confirmer (Départ)'),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: Colors.purple.shade800,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Nouveau'),
        onPressed: () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => StockExitScreen(agent: widget.agent)));
          _loadExits();
        },
      ),
    );
  }
}
