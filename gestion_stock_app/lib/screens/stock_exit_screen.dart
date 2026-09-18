import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/item_models.dart';
import '../models/stock_card.dart';
import '../services/api_service.dart';
import '../widgets/stock_card_item.dart';

class StockExitScreen extends StatefulWidget {
  final Agent agent;

  const StockExitScreen({super.key, required this.agent});

  @override
  State<StockExitScreen> createState() => _StockExitScreenState();
}

class _StockExitScreenState extends State<StockExitScreen> {
  List<StockCard> _stockList = [];
  List<StockCard> _filteredList = [];
  List<ClientItem> _clients = [];
  bool _isLoading = true;
  String _searchQuery = '';
  String _selectedGarageFilter = 'ALL';

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
        _clients = bootstrap['clients'] as List<ClientItem>;
        _applyFilters();
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

  void _applyFilters() {
    setState(() {
      _filteredList = _stockList.where((item) {
        final matchesSearch = item.productName.toLowerCase().contains(_searchQuery.toLowerCase()) ||
            item.lot.toLowerCase().contains(_searchQuery.toLowerCase()) ||
            item.dum.toLowerCase().contains(_searchQuery.toLowerCase());
        final matchesGarage = _selectedGarageFilter == 'ALL' || item.garage == _selectedGarageFilter;
        return matchesSearch && matchesGarage;
      }).toList();
    });
  }

  void _openExitDialog(StockCard item) {
    int? selectedClientId = _clients.isNotEmpty ? _clients.first.id : null;
    final qtyController = TextEditingController();
    DateTime exitDate = DateTime.now();
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
                        'Sortie : ',
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Lot:  • DUM:  • Garage: ',
                    style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Disponible en stock :  colis',
                    style: TextStyle(color: Colors.green.shade800, fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                  const Divider(height: 24),

                  // Sélection Client
                  DropdownButtonFormField<int>(
                    value: selectedClientId,
                    decoration: InputDecoration(
                      labelText: 'Client destinataire',
                      prefixIcon: const Icon(Icons.person),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    items: _clients.map((c) {
                      return DropdownMenuItem(value: c.id, child: Text(c.name));
                    }).toList(),
                    onChanged: (val) => setModalState(() => selectedClientId = val),
                  ),
                  const SizedBox(height: 14),

                  // Quantité
                  TextFormField(
                    controller: qtyController,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: 'Quantité à sortir (colis)',
                      prefixIcon: const Icon(Icons.remove_circle_outline),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Bouton Valider Sortie
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

                              setModalState(() => isDialogSubmitting = true);

                              final payload = {
                                'product_id': item.productId,
                                'garage': item.garage,
                                'frigo': item.frigo,
                                'lot': item.lot,
                                'dum': item.dum,
                                'calibre': item.calibre,
                                'weight': item.weight,
                                'qty': qty,
                                'client_id': selectedClientId,
                                'date': DateTime.now().toIso8601String().split('T')[0],
                                'agent_id': widget.agent.id,
                                'ste_id': item.steId,
                              };

                              try {
                                final res = await ApiService.createExit(payload);
                                Navigator.pop(ctx);
                                _loadData(); // Rafraîchir la liste des stocks

                                final isOffline = res['status'] == 'offline';
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(res['message'] ?? 'Sortie enregistrée !'),
                                    backgroundColor: isOffline ? Colors.orange : Colors.green,
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
                        backgroundColor: Colors.red.shade700,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: isDialogSubmitting
                          ? const CircularProgressIndicator(color: Colors.white)
                          : const Text(
                              'Confirmer la Sortie de Stock',
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
    final garagesAvailable = ['ALL', ..._stockList.map((e) => e.garage).toSet().toList()];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sortie de Stock'),
        backgroundColor: Colors.red.shade700,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: Column(
        children: [
          // Barre de recherche
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Rechercher un produit, lot, DUM...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchQuery = '';
                          _applyFilters();
                        },
                      )
                    : null,
                filled: true,
                fillColor: Colors.grey.shade100,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
              onChanged: (v) {
                _searchQuery = v;
                _applyFilters();
              },
            ),
          ),

          // Filtre rapide par Garage
          if (garagesAvailable.length > 2)
            SizedBox(
              height: 36,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                itemCount: garagesAvailable.length,
                itemBuilder: (ctx, i) {
                  final g = garagesAvailable[i];
                  final isSelected = _selectedGarageFilter == g;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(g == 'ALL' ? 'Tous les garages' : g.toUpperCase()),
                      selected: isSelected,
                      onSelected: (val) {
                        setState(() {
                          _selectedGarageFilter = g;
                          _applyFilters();
                        });
                      },
                    ),
                  );
                },
              ),
            ),

          const SizedBox(height: 8),

          // Liste des cartes
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _filteredList.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.inventory_2_outlined, size: 64, color: Colors.grey.shade400),
                            const SizedBox(height: 12),
                            Text(
                              'Aucun stock disponible',
                              style: TextStyle(color: Colors.grey.shade600, fontSize: 16),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        itemCount: _filteredList.length,
                        itemBuilder: (ctx, i) {
                          final item = _filteredList[i];
                          return StockCardItem(
                            item: item,
                            onTap: () => _openExitDialog(item),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
