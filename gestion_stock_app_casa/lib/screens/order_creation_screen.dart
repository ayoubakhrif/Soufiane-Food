import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/item_models.dart';
import '../services/api_service.dart';

class OrderCreationScreen extends StatefulWidget {
  final Agent agent;
  const OrderCreationScreen({super.key, required this.agent});
  @override
  State<OrderCreationScreen> createState() => _OrderCreationScreenState();
}

class _OrderCreationScreenState extends State<OrderCreationScreen> {
  bool _isLoading = true;
  List<ClientItem> _clients = [];
  List<ProductItem> _products = [];
  
  ClientItem? _selectedClient;
  final List<Map<String, dynamic>> _lines = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final bootstrap = await ApiService.fetchBootstrap();
      if (!mounted) return;
      setState(() {
        _clients = bootstrap['clients'];
        _products = bootstrap['products'];
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showAddLineModal() {
    ProductItem? selectedProduct;
    final qtyController = TextEditingController(text: '1');
    final weightController = TextEditingController(text: '0');
    final noteController = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Container(
              padding: EdgeInsets.only(left: 20, right: 20, top: 20, bottom: MediaQuery.of(ctx).viewInsets.bottom + 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Ajouter un Produit', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<ProductItem>(
                    decoration: const InputDecoration(labelText: 'Produit', border: OutlineInputBorder()),
                    items: _products.map((p) => DropdownMenuItem(value: p, child: Text(p.name))).toList(),
                    onChanged: (v) => setModalState(() => selectedProduct = v),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: qtyController,
                          decoration: const InputDecoration(labelText: 'Unités (Qté)', border: OutlineInputBorder()),
                          keyboardType: TextInputType.number,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextFormField(
                          controller: weightController,
                          decoration: const InputDecoration(labelText: 'Poids Unitaire (Kg)', border: OutlineInputBorder()),
                          keyboardType: TextInputType.number,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: noteController,
                    decoration: const InputDecoration(labelText: 'Note Spécifique (Calibre, Emballage...)', border: OutlineInputBorder()),
                    maxLines: 2,
                  ),
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(backgroundColor: Colors.blue.shade700, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14)),
                      onPressed: () {
                        if (selectedProduct == null) return;
                        setState(() {
                          _lines.add({
                            'product_id': selectedProduct!.id,
                            'product_name': selectedProduct!.name,
                            'quantity': double.tryParse(qtyController.text) ?? 1.0,
                            'weight': double.tryParse(weightController.text) ?? 0.0,
                            'note': noteController.text,
                          });
                        });
                        Navigator.pop(context);
                      },
                      child: const Text('Ajouter'),
                    ),
                  )
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _submitOrder() async {
    if (_selectedClient == null || _lines.isEmpty) return;
    setState(() => _isLoading = true);
    try {
      await ApiService.createOrder({
        'commercial_id': widget.agent.id,
        'client_id': _selectedClient!.id,
        'lines': _lines,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Commande envoyée avec succès!'), backgroundColor: Colors.green));
      Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()), backgroundColor: Colors.red));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nouvelle Commande'), backgroundColor: Colors.blue.shade900, foregroundColor: Colors.white),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<ClientItem>(
                  decoration: const InputDecoration(labelText: 'Sélectionner le Client', border: OutlineInputBorder()),
                  items: _clients.map((c) => DropdownMenuItem(value: c, child: Text(c.name))).toList(),
                  onChanged: (v) => setState(() => _selectedClient = v),
                ),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Lignes de Produit', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    TextButton.icon(
                      icon: const Icon(Icons.add),
                      label: const Text('Ajouter'),
                      onPressed: _showAddLineModal,
                    )
                  ],
                ),
                const Divider(),
                Expanded(
                  child: ListView.builder(
                    itemCount: _lines.length,
                    itemBuilder: (context, index) {
                      final line = _lines[index];
                      final tonnage = line['quantity'] * line['weight'];
                      return Card(
                        child: ListTile(
                          title: Text(line['product_name'], style: const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Text('Qté: ${line['quantity']} | Poids: ${line['weight']} Kg | Total: $tonnage Kg\nNote: ${line['note']}'),
                          trailing: IconButton(
                            icon: const Icon(Icons.delete, color: Colors.red),
                            onPressed: () => setState(() => _lines.removeAt(index)),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.green.shade600, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 16)),
                    onPressed: _selectedClient == null || _lines.isEmpty ? null : _submitOrder,
                    child: const Text('Envoyer la Commande', style: TextStyle(fontSize: 18)),
                  ),
                )
              ],
            ),
          ),
    );
  }
}
