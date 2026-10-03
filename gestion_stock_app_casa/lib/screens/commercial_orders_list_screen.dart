import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../services/api_service.dart';
import 'order_creation_screen.dart';

class CommercialOrdersListScreen extends StatefulWidget {
  final Agent agent;
  const CommercialOrdersListScreen({super.key, required this.agent});

  @override
  State<CommercialOrdersListScreen> createState() => _CommercialOrdersListScreenState();
}

class _CommercialOrdersListScreenState extends State<CommercialOrdersListScreen> {
  bool _isLoading = true;
  List<Map<String, dynamic>> _orders = [];

  @override
  void initState() {
    super.initState();
    _loadOrders();
  }

  Future<void> _loadOrders() async {
    setState(() => _isLoading = true);
    try {
      final list = await ApiService.fetchCommercialOrders(widget.agent.id);
      if (!mounted) return;
      setState(() {
        _orders = list;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Color _getStateColor(String state) {
    if (state == 'done') return Colors.green.shade600;
    return Colors.orange.shade600;
  }

  String _getStateText(String state) {
    if (state == 'done') return 'Réalisé';
    return 'En attente';
  }

  void _showOrderDetails(Map<String, dynamic> order) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        final lines = order['lines'] as List;
        return Container(
          padding: const EdgeInsets.all(20),
          height: MediaQuery.of(context).size.height * 0.7,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Commande ${order['name']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              Text('Client : ${order['client_name']}', style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 16),
              Expanded(
                child: ListView.builder(
                  itemCount: lines.length,
                  itemBuilder: (context, index) {
                    final line = lines[index];
                    return Card(
                      child: ListTile(
                        title: Text(line['product_name'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text('Qté: ${line['quantity']} | Poids: ${line['weight']} Kg | Total: ${line['tonnage']} Kg\nNote: ${line['note']}'),
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
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mes Commandes'),
        backgroundColor: Colors.blue.shade900,
        foregroundColor: Colors.white,
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : _orders.isEmpty 
          ? const Center(child: Text('Aucune commande trouvée'))
          : RefreshIndicator(
              onRefresh: _loadOrders,
              child: ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: _orders.length,
                itemBuilder: (context, index) {
                  final order = _orders[index];
                  return Card(
                    elevation: 3,
                    margin: const EdgeInsets.only(bottom: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: ListTile(
                      contentPadding: const EdgeInsets.all(16),
                      title: Text('${order['name']} - ${order['client_name']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      subtitle: Text('Date: ${order['date']}'),
                      trailing: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: _getStateColor(order['state']).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: _getStateColor(order['state'])),
                        ),
                        child: Text(_getStateText(order['state']), style: TextStyle(color: _getStateColor(order['state']), fontWeight: FontWeight.bold)),
                      ),
                      onTap: () => _showOrderDetails(order),
                    ),
                  );
                },
              ),
            ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: Colors.green.shade700,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Nouveau'),
        onPressed: () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => OrderCreationScreen(agent: widget.agent)));
          _loadOrders();
        },
      ),
    );
  }
}
