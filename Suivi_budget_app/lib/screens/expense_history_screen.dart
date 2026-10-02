import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/expense_model.dart';
import '../models/category_model.dart';
import '../services/api_service.dart';
import 'receipt_viewer_screen.dart';

class ExpenseHistoryScreen extends StatefulWidget {
  const ExpenseHistoryScreen({super.key});

  @override
  State<ExpenseHistoryScreen> createState() => ExpenseHistoryScreenState();
}

class ExpenseHistoryScreenState extends State<ExpenseHistoryScreen> {
  List<ExpenseModel> _expenses = [];
  List<CategoryModel> _categories = [];
  bool _isLoading = true;
  int? _selectedCategoryId;
  bool _allPeriod = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void refresh() {
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final cats = await ApiService.fetchCategories();
      final exps = await ApiService.fetchExpenses(
        categoryId: _selectedCategoryId,
        allPeriod: _allPeriod,
      );

      if (!mounted) return;
      setState(() {
        _categories = cats;
        _expenses = exps;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final currencyFormat = NumberFormat('#,##0.00', 'fr_FR');

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: const Text(
          'Historique des Dépenses',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: Color(0xFF0F172A),
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Color(0xFF0284C7)),
            onPressed: _loadData,
          ),
        ],
      ),
      body: Column(
        children: [
          // Filtres
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: Colors.white,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Filtre Catégories défilant
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      FilterChip(
                        label: const Text('Toutes'),
                        selected: _selectedCategoryId == null,
                        onSelected: (selected) {
                          if (selected) {
                            setState(() => _selectedCategoryId = null);
                            _loadData();
                          }
                        },
                        selectedColor: const Color(0xFF0284C7),
                        labelStyle: TextStyle(
                          color: _selectedCategoryId == null ? Colors.white : Colors.black87,
                          fontWeight: _selectedCategoryId == null ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                      const SizedBox(width: 8),
                      ..._categories.map((c) {
                        final isSelected = _selectedCategoryId == c.id;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8.0),
                          child: FilterChip(
                            label: Text(c.name),
                            selected: isSelected,
                            onSelected: (selected) {
                              setState(() => _selectedCategoryId = selected ? c.id : null);
                              _loadData();
                            },
                            selectedColor: const Color(0xFF0284C7),
                            labelStyle: TextStyle(
                              color: isSelected ? Colors.white : Colors.black87,
                              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${_expenses.length} dépense(s)',
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                    ),
                    Row(
                      children: [
                        Text(
                          _allPeriod ? 'Toutes les dates' : 'Période en cours',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                        ),
                        Switch(
                          value: _allPeriod,
                          activeColor: const Color(0xFF0284C7),
                          onChanged: (val) {
                            setState(() => _allPeriod = val);
                            _loadData();
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),

          const Divider(height: 1),

          // Liste des dépenses
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: Color(0xFF0284C7)))
                : _expenses.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.receipt_long_outlined, size: 64, color: Colors.grey.shade300),
                            const SizedBox(height: 12),
                            Text(
                              'Aucune dépense trouvée',
                              style: TextStyle(color: Colors.grey.shade600, fontSize: 16),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: _loadData,
                        child: ListView.separated(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          itemCount: _expenses.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final exp = _expenses[index];
                            return Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: Colors.grey.shade100),
                              ),
                              child: Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(10),
                                    decoration: BoxDecoration(
                                      color: Colors.red.shade50,
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Icon(
                                      Icons.arrow_upward_rounded,
                                      color: Colors.red.shade700,
                                      size: 20,
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          exp.categoryName,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w700,
                                            fontSize: 15,
                                            color: Color(0xFF1E293B),
                                          ),
                                        ),
                                        if (exp.description.isNotEmpty) ...[
                                          const SizedBox(height: 2),
                                          Text(
                                            exp.description,
                                            style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                                            maxLines: 2,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ],
                                        const SizedBox(height: 4),
                                        Text(
                                          exp.date,
                                          style: TextStyle(fontSize: 11.5, color: Colors.grey.shade400),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Text(
                                        '- ${currencyFormat.format(exp.amount)} DH',
                                        style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 15,
                                          color: Color(0xFFE53935),
                                        ),
                                      ),
                                      if (exp.hasReceipt) ...[
                                        const SizedBox(height: 6),
                                        InkWell(
                                          onTap: () async {
                                            final url = await ApiService.getReceiptImageUrl(exp.id);
                                            if (!context.mounted) return;
                                            Navigator.push(
                                              context,
                                              MaterialPageRoute(
                                                builder: (_) => ReceiptViewerScreen(
                                                  imageUrl: url,
                                                  title: 'Reçu - ${exp.categoryName} (${exp.date})',
                                                ),
                                              ),
                                            );
                                          },
                                          child: Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                            decoration: BoxDecoration(
                                              color: const Color(0xFF0284C7).withOpacity(0.1),
                                              borderRadius: BorderRadius.circular(8),
                                            ),
                                            child: const Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                Icon(Icons.receipt_long_rounded, size: 14, color: Color(0xFF0284C7)),
                                                SizedBox(width: 4),
                                                Text(
                                                  'Reçu 🧾',
                                                  style: TextStyle(
                                                    fontSize: 11,
                                                    fontWeight: FontWeight.bold,
                                                    color: Color(0xFF0284C7),
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}
