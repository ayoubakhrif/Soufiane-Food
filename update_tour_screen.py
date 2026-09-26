import codecs

code = r'''import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/item_models.dart';
import '../models/stock_card.dart';
import '../services/api_service.dart';

class TourItemLine {
  final StockCard stock;
  final ClientItem client;
  double qty;

  TourItemLine({
    required this.stock,
    required this.client,
    required this.qty,
  });
}

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
  GarageItem? _selectedGarage;
  ClientItem? _lastSelectedClient;

  // List of all items added to this truck's tour
  final List<TourItemLine> _tourLines = [];

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
        if (_clients.isNotEmpty) {
          _lastSelectedClient = _clients.first;
        }
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

  double _getAlreadyAllocatedQty(int stockId) {
    return _tourLines
        .where((line) => line.stock.id == stockId)
        .fold(0.0, (sum, line) => sum + line.qty);
  }

  double get _totalTourQty {
    return _tourLines.fold(0.0, (sum, line) => sum + line.qty);
  }

  int get _distinctClientsCount {
    return _tourLines.map((l) => l.client.id).toSet().length;
  }

  void _openAddToCartModal(StockCard stock) {
    final alreadyAllocated = _getAlreadyAllocatedQty(stock.id);
    final remainingStock = stock.quantity - alreadyAllocated;

    if (remainingStock <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ce lot est déjà entièrement alloué dans cette tournée')),
      );
      return;
    }

    ClientItem? modalClient = _lastSelectedClient ?? (_clients.isNotEmpty ? _clients.first : null);
    final qtyController = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
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
                          width: 85,
                          height: 85,
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
                              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 4),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: Colors.green.shade50,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: Colors.green.shade200),
                              ),
                              child: Text(
                                'Reste dispo : ${remainingStock % 1 == 0 ? remainingStock.toInt() : remainingStock}',
                                style: TextStyle(color: Colors.green.shade800, fontWeight: FontWeight.bold, fontSize: 13),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text('Lot: ${stock.lot.isNotEmpty ? stock.lot : "N/A"}', style: TextStyle(color: Colors.grey.shade800, fontSize: 12)),
                            Text('DUM: ${stock.dum.isNotEmpty ? stock.dum : "N/A"}', style: TextStyle(color: Colors.grey.shade700, fontSize: 12)),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  DropdownButtonFormField<ClientItem>(
                    value: modalClient,
                    decoration: InputDecoration(
                      labelText: 'Pour quel client ?',
                      prefixIcon: const Icon(Icons.person_pin_outlined),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                    ),
                    items: _clients.map((c) => DropdownMenuItem(value: c, child: Text(c.name))).toList(),
                    onChanged: (val) {
                      setModalState(() => modalClient = val);
                      _lastSelectedClient = val;
                    },
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: qtyController,
                    autofocus: true,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(
                      labelText: 'Quantité à charger',
                      hintText: 'Max $remainingStock',
                      prefixIcon: const Icon(Icons.add_shopping_cart_rounded),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      suffixText: 'unités',
                    ),
                  ),
                  const SizedBox(height: 18),
                  ElevatedButton.icon(
                    icon: const Icon(Icons.add_circle_outline),
                    label: const Text('Ajouter au camion', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.purple.shade800,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    onPressed: () {
                      if (modalClient == null) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Veuillez sélectionner un client')),
                        );
                        return;
                      }
                      final val = double.tryParse(qtyController.text.trim()) ?? 0.0;
                      if (val <= 0) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Veuillez entrer une quantité supérieure à 0')),
                        );
                        return;
                      }
                      if (val > remainingStock) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Quantité supérieure au disponible ($remainingStock)')),
                        );
                        return;
                      }

                      setState(() {
                        // Check if line with same stock AND same client exists -> add quantity
                        final existingIndex = _tourLines.indexWhere(
                          (l) => l.stock.id == stock.id && l.client.id == modalClient!.id,
                        );
                        if (existingIndex >= 0) {
                          _tourLines[existingIndex].qty += val;
                        } else {
                          _tourLines.add(TourItemLine(stock: stock, client: modalClient!, qty: val));
                        }
                      });

                      Navigator.pop(ctx);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('${stock.productName} ($val) ajouté pour ${modalClient!.name}'),
                          duration: const Duration(seconds: 2),
                        ),
                      );
                    },
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  void _openCartModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setCartState) {
            return Container(
              height: MediaQuery.of(context).size.height * 0.7,
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Center(
                    child: Container(
                      width: 44,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(2)),
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Contenu du camion (${_tourLines.length} sorties)',
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      if (_tourLines.isNotEmpty)
                        TextButton(
                          onPressed: () {
                            setState(() => _tourLines.clear());
                            setCartState(() {});
                            Navigator.pop(ctx);
                          },
                          child: const Text('Tout vider', style: TextStyle(color: Colors.red)),
                        ),
                    ],
                  ),
                  const Divider(),
                  Expanded(
                    child: _tourLines.isEmpty
                        ? const Center(child: Text('Le camion est vide'))
                        : ListView.separated(
                            itemCount: _tourLines.length,
                            separatorBuilder: (_, __) => const Divider(height: 1),
                            itemBuilder: (context, i) {
                              final line = _tourLines[i];
                              return ListTile(
                                contentPadding: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
                                leading: Container(
                                  width: 46,
                                  height: 46,
                                  decoration: BoxDecoration(
                                    color: Colors.grey.shade100,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: line.stock.imageBase64.isNotEmpty
                                      ? ClipRRect(
                                          borderRadius: BorderRadius.circular(8),
                                          child: Image.memory(
                                            base64Decode(line.stock.imageBase64),
                                            fit: BoxFit.cover,
                                          ),
                                        )
                                      : const Icon(Icons.inventory_2_outlined, color: Colors.grey),
                                ),
                                title: Text(line.stock.productName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                                subtitle: Text('Client: ${line.client.name}\nLot: ${line.stock.lot} | Garage: ${line.stock.garage}', style: const TextStyle(fontSize: 12)),
                                isThreeLine: true,
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                      decoration: BoxDecoration(
                                        color: Colors.purple.shade50,
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: Colors.purple.shade200),
                                      ),
                                      child: Text(
                                        'x${line.qty % 1 == 0 ? line.qty.toInt() : line.qty}',
                                        style: TextStyle(fontWeight: FontWeight.bold, color: Colors.purple.shade800),
                                      ),
                                    ),
                                    IconButton(
                                      icon: const Icon(Icons.delete_outline, color: Colors.red),
                                      onPressed: () {
                                        setState(() => _tourLines.removeAt(i));
                                        setCartState(() {});
                                      },
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                  ),
                  const SizedBox(height: 10),
                  ElevatedButton(
                    onPressed: () => Navigator.pop(ctx),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.grey.shade200,
                      foregroundColor: Colors.black87,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    child: const Text('Fermer le récapitulatif'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  void _submit() async {
    if (_selectedDriver == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez sélectionner un chauffeur')));
      return;
    }
    if (_tourLines.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Le camion est vide. Veuillez ajouter des sorties.')));
      return;
    }

    final date = DateTime.now().toIso8601String().split('T')[0];
    final orderRef = 'TOUR-${_selectedDriver!.name.toUpperCase()}-$date-${DateTime.now().millisecondsSinceEpoch}';

    final parsedLines = _tourLines.map((line) => {
      'product_id': line.stock.productId,
      'client_id': line.client.id,
      'garage': line.stock.garage,
      'frigo': line.stock.frigo,
      'lot': line.stock.lot,
      'dum': line.stock.dum,
      'qty': line.qty,
      'date': date,
    }).toList();

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
    final allocatedQty = _getAlreadyAllocatedQty(stock.id);
    final isSelected = allocatedQty > 0;
    final remainingStock = stock.quantity - allocatedQty;

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
        onTap: () => _openAddToCartModal(stock),
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
                            'Dispo: ${remainingStock % 1 == 0 ? remainingStock.toInt() : remainingStock}',
                            style: TextStyle(
                              color: remainingStock > 0 ? Colors.green : Colors.red,
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                            ),
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
                      BoxShadow(color: Colors.black26, blurRadius: 4, offset: Offset(0, 2)),
                    ],
                  ),
                  child: Text(
                    'x${allocatedQty % 1 == 0 ? allocatedQty.toInt() : allocatedQty}',
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
        title: const Text('Préparation Tournée Camion'),
        backgroundColor: Colors.purple.shade800,
        foregroundColor: Colors.white,
        actions: [
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.local_shipping),
                tooltip: 'Voir le camion',
                onPressed: _openCartModal,
              ),
              if (_tourLines.isNotEmpty)
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(color: Colors.amber, shape: BoxShape.circle),
                    child: Text(
                      '${_tourLines.length}',
                      style: const TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 11),
                    ),
                  ),
                ),
            ],
          ),
        ],
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
                          labelText: '1. Chauffeur (Camion)',
                          prefixIcon: const Icon(Icons.person_pin_circle_outlined),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                        items: _drivers.map((d) => DropdownMenuItem(value: d, child: Text(d.name))).toList(),
                        onChanged: (val) => setState(() => _selectedDriver = val),
                      ),
                      const SizedBox(height: 10),
                      DropdownButtonFormField<GarageItem>(
                        decoration: InputDecoration(
                          labelText: '2. Choisir le Garage source',
                          prefixIcon: const Icon(Icons.warehouse_outlined),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                        items: _garages.map((g) => DropdownMenuItem(value: g, child: Text(g.label))).toList(),
                        onChanged: (val) => setState(() => _selectedGarage = val),
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
                                'Sélectionnez un garage source pour voir\nles produits et les assigner aux clients',
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
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
                        InkWell(
                          onTap: _openCartModal,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Row(
                                children: [
                                  Text(
                                    '${_tourLines.length} sortie(s)',
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    '($_distinctClientsCount client(s))',
                                    style: TextStyle(color: Colors.grey.shade700, fontSize: 12),
                                  ),
                                ],
                              ),
                              Text(
                                'Total: ${_totalTourQty % 1 == 0 ? _totalTourQty.toInt() : _totalTourQty} unités',
                                style: TextStyle(color: Colors.purple.shade700, fontSize: 13, fontWeight: FontWeight.bold),
                              ),
                            ],
                          ),
                        ),
                        const Spacer(),
                        ElevatedButton.icon(
                          icon: const Icon(Icons.check_circle_outline),
                          label: const Text('Valider la tournée', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.purple.shade800,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          onPressed: _tourLines.isNotEmpty ? _submit : null,
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

print("Tour multi-client screen written successfully")
