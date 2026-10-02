import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/item_models.dart';
import '../services/api_service.dart';

class PendingOrdersScreen extends StatefulWidget {
  final Agent agent;
  const PendingOrdersScreen({super.key, required this.agent});
  @override
  State<PendingOrdersScreen> createState() => _PendingOrdersScreenState();
}

class _PendingOrdersScreenState extends State<PendingOrdersScreen> {
  bool _isLoading = true;
  List<Order> _orders = [];

  @override
  void initState() {
    super.initState();
    _loadOrders();
  }

  Future<void> _loadOrders() async {
    setState(() => _isLoading = true);
    try {
      final list = await ApiService.fetchPendingOrders();
      if (!mounted) return;
      setState(() {
        _orders = list.map((e) => Order.fromJson(e)).toList();
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }

  Future<void> _validateOrder(int orderId) async {
    try {
      showDialog(context: context, barrierDismissible: false, builder: (_) => const Center(child: CircularProgressIndicator()));
      await ApiService.validateOrder(orderId);
      if (!mounted) return;
      Navigator.pop(context); // Close loading
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Commande marquée comme préparée', style: TextStyle(color: Colors.white)), backgroundColor: Colors.green));
      _loadOrders();
    } catch (e) {
      if (mounted) {
        Navigator.pop(context); // Close loading
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString(), style: const TextStyle(color: Colors.white)), backgroundColor: Colors.red));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Commandes à Préparer'),
        backgroundColor: Colors.blue.shade900,
        foregroundColor: Colors.white,
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : _orders.isEmpty 
          ? const Center(child: Text('Aucune commande en attente'))
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _orders.length,
              itemBuilder: (context, index) {
                final order = _orders[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  elevation: 4,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(order.name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.blue)),
                            Text(order.date.split(' ')[0], style: const TextStyle(color: Colors.grey)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text('Client: ${order.clientName}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                        Text('Commercial: ${order.commercialName}', style: const TextStyle(color: Colors.black54)),
                        const Divider(height: 24),
                        ...order.lines.map((l) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('• ${l.productName}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                              Row(
                                children: [
                                  Text('Qté: ${l.quantity.toStringAsFixed(0)}'),
                                  const SizedBox(width: 16),
                                  Text('Poids: ${l.weight.toStringAsFixed(2)} Kg'),
                                  const SizedBox(width: 16),
                                  Text('Total: ${l.tonnage.toStringAsFixed(2)} Kg', style: TextStyle(color: Colors.green.shade800, fontWeight: FontWeight.bold)),
                                ],
                              ),
                              if (l.note.isNotEmpty)
                                Container(
                                  margin: const EdgeInsets.only(top: 6),
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(8)),
                                  width: double.infinity,
                                  child: Text('Note: ${l.note}', style: TextStyle(color: Colors.orange.shade900, fontStyle: FontStyle.italic)),
                                ),
                            ],
                          ),
                        )).toList(),
                        const SizedBox(height: 16),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            icon: const Icon(Icons.check_circle_outline),
                            label: const Text('Marquer comme Préparé', style: TextStyle(fontSize: 16)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.green.shade600,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 12),
                            ),
                            onPressed: () => _validateOrder(order.id),
                          ),
                        )
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}
