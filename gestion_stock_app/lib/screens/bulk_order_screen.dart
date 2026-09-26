import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/item_models.dart';
import '../models/stock_card.dart';
import '../services/api_service.dart';

class BulkOrderScreen extends StatefulWidget {
  final Agent agent;
  const BulkOrderScreen({super.key, required this.agent});

  @override
  State<BulkOrderScreen> createState() => _BulkOrderScreenState();
}

class _BulkOrderScreenState extends State<BulkOrderScreen> {
  bool _isLoading = true;
  List<ClientItem> _clients = [];
  List<GarageItem> _garages = [];
  List<DriverItem> _drivers = [];
  List<StockCard> _allStock = [];

  DriverItem? _selectedDriver;
  ClientItem? _selectedClient;
  GarageItem? _selectedGarage;

  final Map<StockCard, double> _selectedQuantities = {};

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final bootstrap = await ApiService.fetchBootstrap();
      final stock = await ApiService.fetchStock();
      if (!mounted) return;
      setState(() {
        _clients = bootstrap['clients'];
        _garages = bootstrap['garages'];
        _drivers = bootstrap['drivers'];
        _allStock = stock;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur de chargement: ')));
      }
    }
  }

  List<StockCard> get _filteredStock {
    if (_selectedGarage == null) return [];
    return _allStock.where((s) => s.garage == _selectedGarage!.key && s.quantity > 0).toList();
  }

  void _submit() async {
    if (_selectedDriver == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez s\u00e9lectionner un chauffeur')));
      return;
    }
    if (_selectedClient == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez s\u00e9lectionner un client')));
      return;
    }

    final date = DateTime.now().toIso8601String().split('T')[0];
    final orderRef = 'CMD--';

    final parsedLines = [];
    _selectedQuantities.forEach((stock, qty) {
      if (qty > 0) {
        parsedLines.add({
          'product_id': stock.productId,
          'client_id': _selectedClient!.id,
          'garage': stock.garage,
          'frigo': stock.frigo,
          'lot': stock.lot,
          'dum': stock.dum,
          'qty': qty,
          'date': date,
        });
      }
    });

    if (parsedLines.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez saisir au moins une quantit\u00e9 valide')));
      return;
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
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['message'] ?? 'Erreur inconnue')));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: ')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Widget _buildStockCard(StockCard stock) {
    double currentQty = _selectedQuantities[stock] ?? 0.0;
    
    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: Colors.grey[200],
                borderRadius: BorderRadius.circular(8),
              ),
              child: stock.imageBase64.isNotEmpty
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.memory(
                        base64Decode(stock.imageBase64),
                        fit: BoxFit.cover,
                        errorBuilder: (c, e, s) => const Icon(Icons.image, size: 40, color: Colors.grey),
                      ),
                    )
                  : const Icon(Icons.inventory, size: 40, color: Colors.grey),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(stock.productName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 4),
                  Text('Lot: ', style: TextStyle(color: Colors.grey[700], fontSize: 13)),
                  Text('DUM: ', style: TextStyle(color: Colors.grey[700], fontSize: 13)),
                  const SizedBox(height: 4),
                  Text('Dispo: ', style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
            SizedBox(
              width: 80,
              child: TextFormField(
                initialValue: currentQty == 0 ? '' : currentQty.toString(),
                decoration: const InputDecoration(
                  labelText: 'Qt\u00e9',
                  border: OutlineInputBorder(),
                  contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                ),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                onChanged: (val) {
                  final qty = double.tryParse(val) ?? 0.0;
                  _selectedQuantities[stock] = qty;
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredStock;
    return Scaffold(
      appBar: AppBar(title: const Text('Commande Group\u00e9e / Tourn\u00e9e'), backgroundColor: Colors.purple),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Container(
                  color: Colors.white,
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    children: [
                      DropdownButtonFormField<DriverItem>(
                        decoration: const InputDecoration(labelText: '1. Chauffeur', border: OutlineInputBorder()),
                        items: _drivers.map((d) => DropdownMenuItem(value: d, child: Text(d.name))).toList(),
                        onChanged: (val) => setState(() => _selectedDriver = val),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<ClientItem>(
                        decoration: const InputDecoration(labelText: '2. Client', border: OutlineInputBorder()),
                        items: _clients.map((c) => DropdownMenuItem(value: c, child: Text(c.name))).toList(),
                        onChanged: (val) => setState(() => _selectedClient = val),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<GarageItem>(
                        decoration: const InputDecoration(labelText: '3. Garage / Frigo', border: OutlineInputBorder()),
                        items: _garages.map((g) => DropdownMenuItem(value: g, child: Text(g.label))).toList(),
                        onChanged: (val) {
                          setState(() {
                            _selectedGarage = val;
                            _selectedQuantities.clear();
                          });
                        },
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1, thickness: 1),
                Expanded(
                  child: _selectedGarage == null
                      ? const Center(child: Text('Veuillez s\u00e9lectionner un garage pour voir le stock', style: TextStyle(color: Colors.grey)))
                      : filtered.isEmpty
                          ? const Center(child: Text('Aucun stock disponible dans ce garage', style: TextStyle(color: Colors.grey)))
                          : ListView.builder(
                              itemCount: filtered.length,
                              itemBuilder: (context, i) => _buildStockCard(filtered[i]),
                            ),
                ),
                if (_selectedGarage != null)
                  Padding(
                    padding: const EdgeInsets.all(12.0),
                    child: SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.check),
                        label: const Text('Valider la commande', style: TextStyle(fontSize: 16)),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.purple, foregroundColor: Colors.white),
                        onPressed: _submit,
                      ),
                    ),
                  )
              ],
            ),
    );
  }
}
