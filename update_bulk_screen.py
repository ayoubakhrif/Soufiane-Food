import codecs

code = r'''import 'dart:convert';
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

  final Map<int, double> _selectedQuantities = {};

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
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur de chargement: $e')));
      }
    }
  }

  List<StockCard> get _filteredStock {
    if (_selectedGarage == null) return [];
    return _allStock.where((s) => s.garage == _selectedGarage!.key && s.quantity > 0).toList();
  }

  int get _selectedItemsCount {
    return _selectedQuantities.values.where((q) => q > 0).length;
  }

  double get _totalQuantity {
    return _selectedQuantities.values.fold(0.0, (sum, q) => sum + q);
  }

  void _openQuantityModal(StockCard stock) {
    final currentQty = _selectedQuantities[stock.id] ?? 0.0;
    final qtyController = TextEditingController(text: currentQty > 0 ? (currentQty % 1 == 0 ? currentQty.toInt().toString() : currentQty.toString()) : '');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 44,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      width: 90,
                      height: 90,
                      color: Colors.grey.shade100,
                      child: stock.imageBase64.isNotEmpty
                          ? Image.memory(
                              base64Decode(stock.imageBase64),
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => const Icon(Icons.inventory_2_outlined, size: 40, color: Colors.grey),
                            )
                          : const Icon(Icons.inventory_2_outlined, size: 40, color: Colors.grey),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          stock.productName,
                          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: Colors.green.shade50,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: Colors.green.shade200),
                          ),
                          child: Text(
                            'Disponible : ${stock.quantity % 1 == 0 ? stock.quantity.toInt() : stock.quantity} unités',
                            style: TextStyle(color: Colors.green.shade800, fontWeight: FontWeight.bold, fontSize: 13),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Lot: ${stock.lot.isNotEmpty ? stock.lot : "N/A"}',
                          style: TextStyle(color: Colors.grey.shade800, fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                        Text(
                          'DUM: ${stock.dum.isNotEmpty ? stock.dum : "N/A"}',
                          style: TextStyle(color: Colors.grey.shade700, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              TextField(
                controller: qtyController,
                autofocus: true,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: InputDecoration(
                  labelText: 'Quantité à ajouter',
                  hintText: 'Max ${stock.quantity}',
                  prefixIcon: const Icon(Icons.shopping_bag_outlined),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  suffixText: 'unités',
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  if (currentQty > 0) ...[
                    OutlinedButton(
                      onPressed: () {
                        setState(() {
                          _selectedQuantities.remove(stock.id);
                        });
                        Navigator.pop(ctx);
                      },
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.red,
                        side: const BorderSide(color: Colors.red),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: const Icon(Icons.delete_outline),
                    ),
                    const SizedBox(width: 10),
                  ],
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () {
                        final val = double.tryParse(qtyController.text.trim()) ?? 0.0;
                        if (val <= 0) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Veuillez entrer une quantité supérieure à 0')),
                          );
                          return;
                        }
                        if (val > stock.quantity) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Quantité supérieure au stock disponible (${stock.quantity})')),
                          );
                          return;
                        }
                        setState(() {
                          _selectedQuantities[stock.id] = val;
                        });
                        Navigator.pop(ctx);
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.purple.shade700,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: Text(
                        currentQty > 0 ? 'Mettre à jour' : 'Ajouter à la commande',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  void _submit() async {
    if (_selectedDriver == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez sélectionner un chauffeur')));
      return;
    }
    if (_selectedClient == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez sélectionner un client')));
      return;
    }

    final date = DateTime.now().toIso8601String().split('T')[0];
    final orderRef = 'CMD-$date-${DateTime.now().millisecondsSinceEpoch}';

    final parsedLines = [];
    for (final stock in _allStock) {
      final qty = _selectedQuantities[stock.id] ?? 0.0;
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
    }

    if (parsedLines.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez sélectionner au moins un produit')));
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
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Widget _buildProductSquare(StockCard stock) {
    final qty = _selectedQuantities[stock.id] ?? 0.0;
    final isSelected = qty > 0;

    return Card(
      elevation: isSelected ? 4 : 1.5,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: isSelected ? Colors.purple.shade600 : Colors.grey.shade200,
          width: isSelected ? 2.5 : 1,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _openQuantityModal(stock),
        child: Stack(
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: Container(
                    color: Colors.grey.shade100,
                    child: stock.imageBase64.isNotEmpty
                        ? Image.memory(
                            base64Decode(stock.imageBase64),
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Center(
                              child: Icon(Icons.inventory_2_outlined, size: 48, color: Colors.grey.shade400),
                            ),
                          )
                        : Center(
                            child: Icon(Icons.inventory_2_outlined, size: 48, color: Colors.grey.shade400),
                          ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        stock.productName,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Flexible(
                            child: Text(
                              'Lot: ${stock.lot.isNotEmpty ? stock.lot : "-"}',
                              style: TextStyle(color: Colors.grey.shade600, fontSize: 11),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Text(
                            'Dispo: ${stock.quantity % 1 == 0 ? stock.quantity.toInt() : stock.quantity}',
                            style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold, fontSize: 12),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (isSelected)
              Positioned(
                top: 8,
                right: 8,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.purple.shade700,
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: const [
                      BoxBoxShadow(color: Colors.black26, blurRadius: 4, offset: Offset(0, 2)),
                    ],
                  ),
                  child: Text(
                    'x${qty % 1 == 0 ? qty.toInt() : qty}',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                  ),
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
      appBar: AppBar(
        title: const Text('Commande Groupée / Tournée'),
        backgroundColor: Colors.purple.shade800,
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Container(
                  color: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  child: Column(
                    children: [
                      DropdownButtonFormField<DriverItem>(
                        decoration: InputDecoration(
                          labelText: '1. Chauffeur',
                          prefixIcon: const Icon(Icons.local_shipping_outlined),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                        items: _drivers.map((d) => DropdownMenuItem(value: d, child: Text(d.name))).toList(),
                        onChanged: (val) => setState(() => _selectedDriver = val),
                      ),
                      const SizedBox(height: 10),
                      DropdownButtonFormField<ClientItem>(
                        decoration: InputDecoration(
                          labelText: '2. Client',
                          prefixIcon: const Icon(Icons.person_outline),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                        items: _clients.map((c) => DropdownMenuItem(value: c, child: Text(c.name))).toList(),
                        onChanged: (val) => setState(() => _selectedClient = val),
                      ),
                      const SizedBox(height: 10),
                      DropdownButtonFormField<GarageItem>(
                        decoration: InputDecoration(
                          labelText: '3. Garage / Frigo',
                          prefixIcon: const Icon(Icons.warehouse_outlined),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
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
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.touch_app_outlined, size: 54, color: Colors.grey.shade400),
                              const SizedBox(height: 12),
                              Text(
                                'Veuillez sélectionner un garage\npour afficher les produits disponibles',
                                textAlign: TextAlign.center,
                                style: TextStyle(color: Colors.grey.shade600, fontSize: 15),
                              ),
                            ],
                          ),
                        )
                      : filtered.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.inventory_2_outlined, size: 54, color: Colors.grey.shade400),
                                  const SizedBox(height: 12),
                                  Text(
                                    'Aucun stock disponible dans ce garage',
                                    style: TextStyle(color: Colors.grey.shade600, fontSize: 15),
                                  ),
                                ],
                              ),
                            )
                          : GridView.builder(
                              padding: const EdgeInsets.all(12),
                              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: 2,
                                childAspectRatio: 0.95,
                                crossAxisSpacing: 12,
                                mainAxisSpacing: 12,
                              ),
                              itemCount: filtered.length,
                              itemBuilder: (context, i) => _buildProductSquare(filtered[i]),
                            ),
                ),
                if (_selectedGarage != null)
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.06),
                          offset: const Offset(0, -4),
                          blurRadius: 10,
                        ),
                      ],
                    ),
                    child: SafeArea(
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  '$_selectedItemsCount produit(s) sélectionné(s)',
                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                ),
                                Text(
                                  'Total: ${_totalQuantity % 1 == 0 ? _totalQuantity.toInt() : _totalQuantity} unités',
                                  style: TextStyle(color: Colors.purple.shade700, fontSize: 13, fontWeight: FontWeight.w600),
                                ),
                              ],
                            ),
                          ),
                          ElevatedButton.icon(
                            icon: const Icon(Icons.check_circle_outline),
                            label: const Text('Valider la tournée', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.purple.shade800,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                            onPressed: _selectedItemsCount > 0 ? _submit : null,
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
    );
  }
}
'''

with codecs.open('gestion_stock_app/lib/screens/bulk_order_screen.dart', 'w', encoding='utf-8') as f:
    f.write(code)

print("Saved new bulk_order_screen.dart")
