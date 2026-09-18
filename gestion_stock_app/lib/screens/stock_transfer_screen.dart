import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/item_models.dart';
import '../models/stock_card.dart';
import '../services/api_service.dart';
import '../widgets/stock_card_item.dart';

class StockTransferScreen extends StatefulWidget {
  final Agent agent;

  const StockTransferScreen({super.key, required this.agent});

  @override
  State<StockTransferScreen> createState() => _StockTransferScreenState();
}

class _StockTransferScreenState extends State<StockTransferScreen> {
  List<StockCard> _stockList = [];
  List<GarageItem> _garages = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final stockFuture = ApiService.fetchStock();
      final bootstrapFuture = ApiService.fetchBootstrap();

      final results = await Future.wait([stockFuture, bootstrapFuture]);
      final stock = results[0] as List<StockCard>;
      final bootstrap = results[1] as Map<String, dynamic>;

      setState(() {
        _stockList = stock;
        _garages = bootstrap['garages'] as List<GarageItem>;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur: ')),
      );
      setState(() => _isLoading = false);
    }
  }

  void _openTransferDialog(StockCard item) {
    String? destGarage = _garages.where((g) => g.key != item.garage).isNotEmpty
        ? _garages.where((g) => g.key != item.garage).first.key
        : null;

    final qtyController = TextEditingController();
    DateTime transferDate = DateTime.now();
    bool isDialogSubmitting = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Transfert : ',
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Lot:  • DUM: ',
                    style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                  ),
                  Text(
                    'Garage actuel (Source) : ',
                    style: TextStyle(color: Colors.blue.shade900, fontWeight: FontWeight.w600, fontSize: 13),
                  ),
                  Text(
                    'Disponible :  colis',
                    style: TextStyle(color: Colors.green.shade800, fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                  const Divider(height: 24),

                  // Garage Destination
                  DropdownButtonFormField<String>(
                    value: destGarage,
                    decoration: InputDecoration(
                      labelText: 'Garage de Destination',
                      prefixIcon: const Icon(Icons.move_to_inbox),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    items: _garages.where((g) => g.key != item.garage).map((g) {
                      return DropdownMenuItem(value: g.key, child: Text(g.label));
                    }).toList(),
                    onChanged: (val) => setModalState(() => destGarage = val),
                  ),
                  const SizedBox(height: 14),

                  // Quantité
                  TextFormField(
                    controller: qtyController,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: 'Quantité à transférer (colis)',
                      prefixIcon: const Icon(Icons.swap_horiz),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Bouton Valider Transfert
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton(
                      onPressed: isDialogSubmitting
                          ? null
                          : () async {
                              final qty = double.tryParse(qtyController.text.replaceAll(',', '.')) ?? 0.0;
                              if (qty <= 0) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('Veuillez entrer une quantité valide.')),
                                );
                                return;
                              }
                              if (qty > item.quantity) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('Quantité supérieure au stock dispo () !')),
                                );
                                return;
                              }
                              if (destGarage == null) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('Veuillez choisir un garage de destination.')),
                                );
                                return;
                              }

                              setModalState(() => isDialogSubmitting = true);

                              final payload = {
                                'product_id': item.productId,
                                'garage_source': item.garage,
                                'garage_dest': destGarage,
                                'frigo_source': item.frigo,
                                'frigo_dest': item.frigo,
                                'lot': item.lot,
                                'dum': item.dum,
                                'calibre': item.calibre,
                                'weight': item.weight,
                                'qty': qty,
                                'date': DateTime.now().toIso8601String().split('T')[0],
                                'agent_id': widget.agent.id,
                                'ste_id': item.steId,
                              };

                              try {
                                final res = await ApiService.createTransfer(payload);
                                Navigator.pop(ctx);
                                _loadData(); // Rafraîchir l'écran

                                final isOffline = res['status'] == 'offline';
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(res['message'] ?? 'Transfert effectué !'),
                                    backgroundColor: isOffline ? Colors.orange : Colors.blue.shade700,
                                  ),
                                );
                              } catch (e) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('Erreur: '), backgroundColor: Colors.red),
                                );
                              } finally {
                                setModalState(() => isDialogSubmitting = false);
                              }
                            },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blue.shade800,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: isDialogSubmitting
                          ? const CircularProgressIndicator(color: Colors.white)
                          : const Text(
                              'Valider le Transfert',
                              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                            ),
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Transfert de Stock'),
        backgroundColor: Colors.blue.shade800,
        foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _stockList.isEmpty
              ? const Center(child: Text('Aucun produit disponible à transférer.'))
              : ListView.builder(
                  itemCount: _stockList.length,
                  itemBuilder: (ctx, i) {
                    final item = _stockList[i];
                    return StockCardItem(
                      item: item,
                      onTap: () => _openTransferDialog(item),
                    );
                  },
                ),
    );
  }
}
