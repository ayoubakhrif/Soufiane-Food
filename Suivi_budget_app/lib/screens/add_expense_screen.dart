import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import '../models/category_model.dart';
import '../services/api_service.dart';

class AddExpenseScreen extends StatefulWidget {
  final VoidCallback onExpenseAdded;

  const AddExpenseScreen({
    super.key,
    required this.onExpenseAdded,
  });

  @override
  State<AddExpenseScreen> createState() => _AddExpenseScreenState();
}

class _AddExpenseScreenState extends State<AddExpenseScreen> {
  final _amountController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _monthlyCategoryController = TextEditingController(text: 'Loyer');
  final _picker = ImagePicker();

  bool _isMonthly = false; // Bascule entre Sortie Quotidienne et Charge Mensuelle
  DateTime _selectedDate = DateTime.now();
  int? _selectedCategoryId;
  List<CategoryModel> _categories = [];
  bool _loadingCategories = true;
  bool _isSubmitting = false;

  XFile? _receiptFile;
  Uint8List? _receiptBytes;

  final List<String> _suggestedMonthlyCategories = [
    'Loyer',
    'Internet / Télécom',
    'Eau & Électricité',
    'Assurance',
    'Scolarité',
    'Abonnement',
    'Autre charge',
  ];

  @override
  void initState() {
    super.initState();
    _loadCategories();
  }

  @override
  void dispose() {
    _amountController.dispose();
    _descriptionController.dispose();
    _monthlyCategoryController.dispose();
    super.dispose();
  }

  Future<void> _loadCategories() async {
    try {
      final list = await ApiService.fetchCategories();
      if (!mounted) return;
      setState(() {
        _categories = list;
        _loadingCategories = false;
        if (_categories.isNotEmpty) {
          _selectedCategoryId = _categories.first.id;
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingCategories = false);
    }
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final file = await _picker.pickImage(
        source: source,
        maxWidth: 1280,
        maxHeight: 1280,
        imageQuality: 80,
      );

      if (file != null) {
        final bytes = await file.readAsBytes();
        setState(() {
          _receiptFile = file;
          _receiptBytes = bytes;
        });
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur lors de la capture : $e')),
      );
    }
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 30)),
    );
    if (picked != null) {
      setState(() => _selectedDate = picked);
    }
  }

  Future<void> _submitExpense() async {
    final amountText = _amountController.text.trim().replaceAll(',', '.');
    final amount = double.tryParse(amountText);

    if (amount == null || amount <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Veuillez saisir un montant valide supérieur à 0'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    if (!_isMonthly && _selectedCategoryId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Veuillez sélectionner une catégorie'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      if (_isMonthly) {
        // Enregistrement d'une Charge Mensuelle Fixe
        final catName = _monthlyCategoryController.text.trim().isNotEmpty
            ? _monthlyCategoryController.text.trim()
            : 'Charge fixe';

        await ApiService.createExpense(
          amount: amount,
          isMonthly: true,
          categoryName: catName,
          description: _descriptionController.text.trim(),
        );

        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Charge mensuelle enregistrée avec succès ! 📌'),
            backgroundColor: Color(0xFF6366F1),
            behavior: SnackBarBehavior.floating,
          ),
        );
      } else {
        // Enregistrement d'une Sortie Quotidienne
        String? base64Image;
        String? filename;

        if (_receiptBytes != null) {
          base64Image = base64Encode(_receiptBytes!);
          filename = _receiptFile?.name ?? 'recu_${DateTime.now().millisecondsSinceEpoch}.jpg';
        }

        final dateStr = DateFormat('yyyy-MM-dd').format(_selectedDate);

        await ApiService.createExpense(
          amount: amount,
          categoryId: _selectedCategoryId!,
          date: dateStr,
          description: _descriptionController.text.trim(),
          receiptBase64: base64Image,
          receiptFilename: filename,
          isMonthly: false,
        );

        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Sortie quotidienne enregistrée ! 💸'),
            backgroundColor: Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }

      // Réinitialiser formulaire
      _amountController.clear();
      _descriptionController.clear();
      setState(() {
        _receiptFile = null;
        _receiptBytes = null;
        _selectedDate = DateTime.now();
      });

      // Notifier le dashboard pour rafraîchir
      widget.onExpenseAdded();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceAll('Exception: ', '')),
          backgroundColor: Colors.red.shade700,
        ),
      );
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: Text(
          _isMonthly ? 'Nouvelle Charge Mensuelle' : 'Nouvelle Sortie Quotidienne',
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: Color(0xFF0F172A),
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Sélecteur de Type : Sortie vs Charge Mensuelle
            Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: Colors.grey.shade200,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _isMonthly = false),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: !_isMonthly ? Colors.white : Colors.transparent,
                          borderRadius: BorderRadius.circular(10),
                          boxShadow: !_isMonthly
                              ? [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4)]
                              : null,
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.shopping_bag_outlined,
                              size: 16,
                              color: !_isMonthly ? const Color(0xFF0284C7) : Colors.grey.shade600,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Sortie Quotidienne',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: !_isMonthly ? FontWeight.bold : FontWeight.w500,
                                color: !_isMonthly ? const Color(0xFF0284C7) : Colors.grey.shade600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _isMonthly = true),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: _isMonthly ? Colors.white : Colors.transparent,
                          borderRadius: BorderRadius.circular(10),
                          boxShadow: _isMonthly
                              ? [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4)]
                              : null,
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.push_pin_rounded,
                              size: 16,
                              color: _isMonthly ? const Color(0xFF6366F1) : Colors.grey.shade600,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Charge Mensuelle Fixe',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: _isMonthly ? FontWeight.bold : FontWeight.w500,
                                color: _isMonthly ? const Color(0xFF6366F1) : Colors.grey.shade600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Carte Saisie Montant
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.04),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Column(
                children: [
                  Text(
                    _isMonthly ? 'Montant de la charge fixe' : 'Montant de la sortie',
                    style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.baseline,
                    textBaseline: TextBaseline.alphabetic,
                    children: [
                      IntrinsicWidth(
                        child: TextField(
                          controller: _amountController,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 38,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF0F172A),
                          ),
                          decoration: const InputDecoration(
                            hintText: '0.00',
                            hintStyle: TextStyle(color: Color(0xFFCBD5E1)),
                            border: InputBorder.none,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text(
                        'DH',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF64748B),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            if (_isMonthly) ...[
              // Saisie Charge Mensuelle
              const Text(
                'Type de charge récurrente',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              const SizedBox(height: 8),

              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _suggestedMonthlyCategories.map((sug) {
                  final isSelected = _monthlyCategoryController.text == sug;
                  return ChoiceChip(
                    label: Text(sug),
                    selected: isSelected,
                    onSelected: (selected) {
                      if (selected) {
                        setState(() => _monthlyCategoryController.text = sug);
                      }
                    },
                    selectedColor: const Color(0xFF6366F1),
                    backgroundColor: Colors.white,
                    labelStyle: TextStyle(
                      color: isSelected ? Colors.white : const Color(0xFF334155),
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    ),
                  );
                }).toList(),
              ),

              const SizedBox(height: 12),

              TextField(
                controller: _monthlyCategoryController,
                decoration: InputDecoration(
                  labelText: 'Nom de la charge (personnalisé)',
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide(color: Colors.grey.shade200),
                  ),
                ),
              ),
            ] else ...[
              // Sélecteur Catégorie (Sortie Quotidienne)
              const Text(
                'Catégorie',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              const SizedBox(height: 10),

              if (_loadingCategories)
                const Center(child: CircularProgressIndicator())
              else if (_categories.isEmpty)
                const Text('Aucune catégorie trouvée')
              else
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _categories.map((cat) {
                    final isSelected = _selectedCategoryId == cat.id;
                    return ChoiceChip(
                      label: Text(cat.name),
                      selected: isSelected,
                      onSelected: (selected) {
                        if (selected) setState(() => _selectedCategoryId = cat.id);
                      },
                      selectedColor: const Color(0xFF0284C7),
                      backgroundColor: Colors.white,
                      labelStyle: TextStyle(
                        color: isSelected ? Colors.white : const Color(0xFF334155),
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: BorderSide(
                          color: isSelected ? const Color(0xFF0284C7) : Colors.grey.shade300,
                        ),
                      ),
                    );
                  }).toList(),
                ),

              const SizedBox(height: 20),

              // Sélecteur de Date
              InkWell(
                onTap: _pickDate,
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.calendar_today_rounded, color: Color(0xFF0284C7), size: 20),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Date', style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
                            Text(
                              DateFormat('EEEE d MMMM yyyy', 'fr_FR').format(_selectedDate),
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: Colors.grey),
                    ],
                  ),
                ),
              ),
            ],

            const SizedBox(height: 16),

            // Description / Note
            TextField(
              controller: _descriptionController,
              maxLines: 2,
              decoration: InputDecoration(
                labelText: 'Note / Description (optionnel)',
                hintText: _isMonthly ? 'Ex: Loyer appartement, fibre optique...' : 'Ex: Marché hebdomadaire, déjeuner...',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(color: Colors.grey.shade200),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(color: Colors.grey.shade200),
                ),
              ),
            ),

            if (!_isMonthly) ...[
              const SizedBox(height: 20),

              // Photo du reçu / Facture
              const Text(
                'Facture / Reçu de caisse',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              const SizedBox(height: 10),

              if (_receiptBytes != null)
                Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: Row(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: Image.memory(
                          _receiptBytes!,
                          width: 70,
                          height: 70,
                          fit: BoxFit.cover,
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Photo prête',
                              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              '${(_receiptBytes!.lengthInBytes / 1024).toStringAsFixed(1)} Ko',
                              style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.delete_outline_rounded, color: Colors.red),
                        onPressed: () {
                          setState(() {
                            _receiptFile = null;
                            _receiptBytes = null;
                          });
                        },
                      ),
                    ],
                  ),
                )
              else
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickImage(ImageSource.camera),
                        icon: const Icon(Icons.camera_alt_rounded, size: 20),
                        label: const Text('Appareil photo'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          side: BorderSide(color: Colors.grey.shade300),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickImage(ImageSource.gallery),
                        icon: const Icon(Icons.photo_library_rounded, size: 20),
                        label: const Text('Galerie'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          side: BorderSide(color: Colors.grey.shade300),
                        ),
                      ),
                    ),
                  ],
                ),
            ],

            const SizedBox(height: 28),

            // Bouton Enregistrer
            SizedBox(
              height: 52,
              child: ElevatedButton(
                onPressed: _isSubmitting ? null : _submitExpense,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _isMonthly ? const Color(0xFF6366F1) : const Color(0xFF0284C7),
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                child: _isSubmitting
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                      )
                    : Text(
                        _isMonthly ? 'Enregistrer la charge mensuelle' : 'Enregistrer la sortie',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
