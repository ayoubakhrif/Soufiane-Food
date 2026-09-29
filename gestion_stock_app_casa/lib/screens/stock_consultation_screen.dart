import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/stock_card.dart';
import '../services/api_service.dart';

class StockConsultationScreen extends StatefulWidget {
  final Agent agent;

  const StockConsultationScreen({super.key, required this.agent});

  @override
  State<StockConsultationScreen> createState() => _StockConsultationScreenState();
}

class _StockConsultationScreenState extends State<StockConsultationScreen> {
  bool _isLoading = true;
  List<StockCard> _allStock = [];
  String _searchQuery = '';
  String _selectedFrigo = 'Tous';

  @override
  void initState() {
    super.initState();
    _loadStock();
  }

  Future<void> _loadStock() async {
    try {
      final stock = await ApiService.fetchStock();
      if (!mounted) return;
      setState(() {
        _allStock = stock;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erreur de chargement: $e')),
        );
      }
    }
  }

  List<String> get _availableFrigos {
    final frigos = _allStock.map((s) => s.frigo).toSet().toList();
    frigos.sort();
    return ['Tous', ...frigos];
  }

  List<StockCard> get _filteredStock {
    return _allStock.where((s) {
      if (_selectedFrigo != 'Tous' && s.frigo != _selectedFrigo) return false;
      
      final query = _searchQuery.toLowerCase();
      if (query.isEmpty) return true;

      return s.productName.toLowerCase().contains(query) ||
             s.lot.toLowerCase().contains(query) ||
             s.dum.toLowerCase().contains(query);
    }).toList();
  }

  double get _totalQuantity {
    return _filteredStock.fold(0.0, (sum, item) => sum + item.quantity);
  }

  double get _totalTonnage {
    return _filteredStock.fold(0.0, (sum, item) => sum + (item.quantity * item.weight));
  }

  @override
  Widget build(BuildContext context) {
    final stockList = _filteredStock;

    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      appBar: AppBar(
        title: const Text('Consultation Stock'),
        backgroundColor: Colors.blue.shade800,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Search & Filters
          Container(
            color: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Column(
              children: [
                TextField(
                  decoration: InputDecoration(
                    hintText: 'Rechercher par Produit, Lot ou DUM...',
                    prefixIcon: const Icon(Icons.search, color: Colors.blue),
                    filled: true,
                    fillColor: Colors.blue.shade50,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide.none,
                    ),
                    contentPadding: const EdgeInsets.symmetric(vertical: 0),
                  ),
                  onChanged: (val) {
                    setState(() {
                      _searchQuery = val;
                    });
                  },
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Text('Frigo: ', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: _availableFrigos.map((frigo) {
                            final isSelected = frigo == _selectedFrigo;
                            return Padding(
                              padding: const EdgeInsets.only(right: 8.0),
                              child: ChoiceChip(
                                label: Text(frigo),
                                selected: isSelected,
                                selectedColor: Colors.blue.shade100,
                                labelStyle: TextStyle(
                                  color: isSelected ? Colors.blue.shade800 : Colors.black87,
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                ),
                                onSelected: (selected) {
                                  if (selected) {
                                    setState(() {
                                      _selectedFrigo = frigo;
                                    });
                                  }
                                },
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Global Totals
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
            decoration: BoxDecoration(
              color: Colors.blue.shade50,
              border: Border(bottom: BorderSide(color: Colors.blue.shade100)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Total Unités', style: TextStyle(color: Colors.black54, fontSize: 12)),
                    Text(
                      _totalQuantity.toStringAsFixed(0),
                      style: TextStyle(color: Colors.blue.shade900, fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    const Text('Tonnage Total', style: TextStyle(color: Colors.black54, fontSize: 12)),
                    Text(
                      '${_totalTonnage.toStringAsFixed(2)} Kg',
                      style: TextStyle(color: Colors.blue.shade900, fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // List
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : stockList.isEmpty
                    ? Center(
                        child: Text(
                          'Aucun stock trouvé.',
                          style: TextStyle(color: Colors.grey.shade600, fontSize: 16),
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: stockList.length,
                        itemBuilder: (context, index) {
                          final stock = stockList[index];
                          final tonnage = stock.quantity * stock.weight;

                          return Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            elevation: 2,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // Image
                                  Container(
                                    width: 80,
                                    height: 80,
                                    decoration: BoxDecoration(
                                      color: Colors.grey.shade100,
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(color: Colors.grey.shade200),
                                    ),
                                    clipBehavior: Clip.hardEdge,
                                    child: stock.imageBase64.isNotEmpty
                                        ? Image.memory(
                                            base64Decode(stock.imageBase64),
                                            fit: BoxFit.cover,
                                            errorBuilder: (_, __, ___) => Icon(Icons.inventory_2, color: Colors.grey.shade400, size: 32),
                                          )
                                        : Icon(Icons.inventory_2, color: Colors.grey.shade400, size: 32),
                                  ),
                                  const SizedBox(width: 16),
                                  
                                  // Details
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          stock.productName,
                                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                        ),
                                        const SizedBox(height: 6),
                                        Row(
                                          children: [
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: Colors.blue.shade50,
                                                borderRadius: BorderRadius.circular(4),
                                              ),
                                              child: Text(
                                                'Lot: ${stock.lot.isEmpty ? "-" : stock.lot}',
                                                style: TextStyle(color: Colors.blue.shade900, fontSize: 12, fontWeight: FontWeight.w600),
                                              ),
                                            ),
                                            const SizedBox(width: 8),
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: Colors.orange.shade50,
                                                borderRadius: BorderRadius.circular(4),
                                              ),
                                              child: Text(
                                                'Frigo: ${stock.frigo}',
                                                style: TextStyle(color: Colors.orange.shade900, fontSize: 12, fontWeight: FontWeight.w600),
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          'DUM: ${stock.dum.isEmpty ? "-" : stock.dum}',
                                          style: TextStyle(color: Colors.grey.shade700, fontSize: 12),
                                        ),
                                        const Divider(height: 16),
                                        Row(
                                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                          children: [
                                            Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                const Text('Unités', style: TextStyle(fontSize: 11, color: Colors.black54)),
                                                Text(
                                                  stock.quantity.toStringAsFixed(0),
                                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                                                ),
                                              ],
                                            ),
                                            Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                const Text('Poids U.', style: TextStyle(fontSize: 11, color: Colors.black54)),
                                                Text(
                                                  '${stock.weight.toStringAsFixed(2)} Kg',
                                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                                ),
                                              ],
                                            ),
                                            Column(
                                              crossAxisAlignment: CrossAxisAlignment.end,
                                              children: [
                                                const Text('Tonnage', style: TextStyle(fontSize: 11, color: Colors.black54)),
                                                Text(
                                                  '${tonnage.toStringAsFixed(2)} Kg',
                                                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.green.shade700),
                                                ),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
