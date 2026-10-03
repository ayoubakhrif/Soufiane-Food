import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../services/api_service.dart';
import '../models/item_models.dart';
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
  List<DriverItem> _drivers = [];

  @override
  void initState() {
    super.initState();
    _loadExits();
  }

  Future<void> _loadExits() async {
    setState(() => _isLoading = true);
    try {
      final list = await ApiService.fetchExits();
      final bootstrap = await ApiService.fetchBootstrap();
      final drvs = bootstrap['drivers'] as List<DriverItem>;
      if (!mounted) return;
      setState(() {
        _exits = list;
        _drivers = drvs;
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

Future<void> _confirmExit(dynamic exit) async {
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
                          Text('Chauffeur: ${exit['driver_name'] ?? "Pas de chauffeur"}'),
                          
                          if (isRegistered) ...[
                            const SizedBox(height: 12),
                            Align(
                              alignment: Alignment.centerRight,
                              child: ElevatedButton.icon(
                                onPressed: () => _confirmExit(exit),
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
