import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/item_models.dart';
import '../services/api_service.dart';

class BulkOrderScreen extends StatefulWidget {
  final Agent agent;
  const BulkOrderScreen({super.key, required this.agent});

  @override
  State<BulkOrderScreen> createState() => _BulkOrderScreenState();
}

class _BulkOrderScreenState extends State<BulkOrderScreen> {
  bool _isLoading = true;
  List<ProductItem> _products = [];
  List<ClientItem> _clients = [];
  List<GarageItem> _garages = [];
  List<DriverItem> _drivers = [];

  DriverItem? _selectedDriver;
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
        _products = bootstrap['products'];
        _clients = bootstrap['clients'];
        _garages = bootstrap['garages'];
        _drivers = bootstrap['drivers'];
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  void _addLine() {
    setState(() {
      _lines.add({
        'product': null,
        'client': null,
        'qty': 0.0,
        'garage': null,
      });
    });
  }

  void _submit() async {
    if (_selectedDriver == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez sélectionner un chauffeur')));
      return;
    }
    if (_lines.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Ajoutez au moins une ligne')));
      return;
    }

    final date = DateTime.now().toIso8601String().split('T')[0];
    final orderRef = 'CMD-$date-{DateTime.now().millisecondsSinceEpoch}';

    final parsedLines = [];
    for (var line in _lines) {
      if (line['product'] == null || line['client'] == null || line['garage'] == null || line['qty'] <= 0) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez remplir toutes les lignes correctement')));
        return;
      }
      parsedLines.add({
        'product_id': (line['product'] as ProductItem).id,
        'client_id': (line['client'] as ClientItem).id,
        'garage': (line['garage'] as GarageItem).key,
        'qty': line['qty'],
        'date': date,
      });
    }

    setState(() => _isLoading = true);
    try {
      final res = await ApiService.createBulkExit({
        'driver_id': _selectedDriver!.id,
        'order_reference': orderRef,
        'lines': parsedLines,
      });
      if (!mounted) return;
      if (res['status'] == 'success') {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['message'])));
        Navigator.pop(context);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['message'])));
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Commande Groupée / Tournée'), backgroundColor: Colors.purple),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: DropdownButtonFormField<DriverItem>(
                  decoration: const InputDecoration(labelText: 'Chauffeur', border: OutlineInputBorder()),
                  items: _drivers.map((d) => DropdownMenuItem(value: d, child: Text(d.name))).toList(),
                  onChanged: (val) => setState(() => _selectedDriver = val),
                ),
              ),
              Expanded(
                child: ListView.builder(
                  itemCount: _lines.length,
                  itemBuilder: (context, i) {
                    final line = _lines[i];
                    return Card(
                      margin: const EdgeInsets.all(8),
                      child: Padding(
                        padding: const EdgeInsets.all(8.0),
                        child: Column(
                          children: [
                            DropdownButtonFormField<ProductItem>(
                              decoration: const InputDecoration(labelText: 'Produit'),
                              items: _products.map((p) => DropdownMenuItem(value: p, child: Text(p.name))).toList(),
                              onChanged: (val) => setState(() => line['product'] = val),
                            ),
                            DropdownButtonFormField<ClientItem>(
                              decoration: const InputDecoration(labelText: 'Client'),
                              items: _clients.map((c) => DropdownMenuItem(value: c, child: Text(c.name))).toList(),
                              onChanged: (val) => setState(() => line['client'] = val),
                            ),
                            DropdownButtonFormField<GarageItem>(
                              decoration: const InputDecoration(labelText: 'Garage Source'),
                              items: _garages.map((g) => DropdownMenuItem(value: g, child: Text(g.label))).toList(),
                              onChanged: (val) => setState(() => line['garage'] = val),
                            ),
                            TextFormField(
                              decoration: const InputDecoration(labelText: 'Quantité'),
                              keyboardType: TextInputType.number,
                              onChanged: (val) => line['qty'] = double.tryParse(val) ?? 0,
                            ),
                            Align(
                              alignment: Alignment.centerRight,
                              child: IconButton(
                                icon: const Icon(Icons.delete, color: Colors.red),
                                onPressed: () => setState(() => _lines.removeAt(i)),
                              ),
                            )
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.add),
                        label: const Text('Ajouter Ligne'),
                        onPressed: _addLine,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.check),
                        label: const Text('Valider'),
                        onPressed: _submit,
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.purple, foregroundColor: Colors.white),
                      ),
                    ),
                  ],
                ),
              )
            ],
          ),
    );
  }
}
