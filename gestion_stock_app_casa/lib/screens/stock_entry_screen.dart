import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/item_models.dart';
import '../services/api_service.dart';
import '../widgets/image_capture_box.dart';

class StockEntryScreen extends StatefulWidget {
  final Agent agent;

  const StockEntryScreen({super.key, required this.agent});

  @override
  State<StockEntryScreen> createState() => _StockEntryScreenState();
}

class _StockEntryScreenState extends State<StockEntryScreen> {
  final _formKey = GlobalKey<FormState>();

  List<ProductItem> _products = [];
  List<GarageItem> _garages = [];
  bool _isLoadingBootstrap = true;
  bool _isSubmitting = false;

  // Form controllers
  int? _selectedProductId;
  String? _selectedGarage;
  final _lotController = TextEditingController();
  final _dumController = TextEditingController();
  final _calibreController = TextEditingController();
  final _qtyController = TextEditingController();
  final _weightController = TextEditingController();
  DateTime _selectedDate = DateTime.now();

  String _photoPackaging = '';
  String _photoContainer = '';

  @override
  void initState() {
    super.initState();
    _loadBootstrap();
  }

  @override
  void dispose() {
    _lotController.dispose();
    _dumController.dispose();
    _calibreController.dispose();
    _qtyController.dispose();
    _weightController.dispose();
    super.dispose();
  }

  Future<void> _loadBootstrap() async {
    try {
      final data = await ApiService.fetchBootstrap();
      setState(() {
        _products = data['products'];
        _garages = data['garages'];
        if (_garages.isNotEmpty) {
          _selectedGarage = _garages.first.key;
        }
        _isLoadingBootstrap = false;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur chargement: ')),
      );
      setState(() => _isLoadingBootstrap = false);
    }
  }

  Future<void> _submitEntry() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedProductId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Veuillez sélectionner un produit.')),
      );
      return;
    }

    setState(() => _isSubmitting = true);

    final payload = {
      'product_id': _selectedProductId,
      'garage': _selectedGarage,
      'frigo': 'stock_casa_field',
      'lot': _lotController.text.trim(),
      'dum': _dumController.text.trim(),
      'calibre': _calibreController.text.trim(),
      'qty': double.tryParse(_qtyController.text.replaceAll(',', '.')) ?? 0.0,
      'weight': double.tryParse(_weightController.text.replaceAll(',', '.')) ?? 0.0,
      'date': DateTime.now().toIso8601String().split('T')[0],
      'agent_id': widget.agent.id,
      'photo_packaging': _photoPackaging.isNotEmpty ? _photoPackaging : null,
      'photo_container': _photoContainer.isNotEmpty ? _photoContainer : null,
    };

    try {
      final res = await ApiService.createEntry(payload);
      if (!mounted) return;

      final isOffline = res['status'] == 'offline';
      final isError = res['status'] == 'error';
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          title: Text(isOffline
              ? 'Enregistré en local'
              : (isError ? 'Erreur' : 'Entrée validée !')),
          content: Text(res['message'] ?? 'Opération effectuée avec succès.'),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(ctx);
                if (!isError) {
                  Navigator.pop(context, true);
                }
              },
              child: const Text('OK'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur: '), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoadingBootstrap) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Entrée de Stock'),
        backgroundColor: Colors.green.shade700,
        foregroundColor: Colors.white,
      ),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Garage
              DropdownButtonFormField<String>(
                value: _selectedGarage,
                decoration: InputDecoration(
                  labelText: 'Garage de réception',
                  prefixIcon: const Icon(Icons.warehouse),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
                items: _garages.map((g) {
                  return DropdownMenuItem(value: g.key, child: Text(g.label));
                }).toList(),
                onChanged: (val) => setState(() => _selectedGarage = val),
              ),
              const SizedBox(height: 14),

              // Produit
              DropdownButtonFormField<int>(
                value: _selectedProductId,
                decoration: InputDecoration(
                  labelText: 'Produit',
                  prefixIcon: const Icon(Icons.inventory_2),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
                items: _products.map((p) {
                  return DropdownMenuItem(value: p.id, child: Text(p.name));
                }).toList(),
                onChanged: (val) => setState(() => _selectedProductId = val),
                validator: (v) => v == null ? 'Sélectionnez un produit' : null,
              ),
              const SizedBox(height: 14),

              // Lot & DUM
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _lotController,
                      decoration: InputDecoration(
                        labelText: 'N° Lot',
                        prefixIcon: const Icon(Icons.tag),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'Requis' : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _dumController,
                      decoration: InputDecoration(
                        labelText: 'DUM',
                        prefixIcon: const Icon(Icons.receipt_long),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'Requis' : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Calibre & Poids unitaire
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _calibreController,
                      decoration: InputDecoration(
                        labelText: 'Calibre',
                        prefixIcon: const Icon(Icons.tune),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _weightController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: InputDecoration(
                        labelText: 'Poids Unit (Kg)',
                        prefixIcon: const Icon(Icons.scale),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Quantité
              TextFormField(
                controller: _qtyController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Quantité (Nombre de colis)',
                  prefixIcon: const Icon(Icons.numbers),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return 'Entrez une quantité';
                  if (double.tryParse(v.replaceAll(',', '.')) == null) return 'Nombre invalide';
                  return null;
                },
              ),
              const SizedBox(height: 20),

              // Section Photos
              const Text(
                'Photos Justificatives',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: ImageCaptureBox(
                      label: 'Photo Emballage',
                      onImageCaptured: (b64) => _photoPackaging = b64,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ImageCaptureBox(
                      label: 'Photo Conteneur',
                      onImageCaptured: (b64) => _photoContainer = b64,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Bouton Validation
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton.icon(
                  onPressed: _isSubmitting ? null : _submitEntry,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green.shade700,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  icon: _isSubmitting
                      ? const SizedBox.shrink()
                      : const Icon(Icons.check_circle_outline),
                  label: _isSubmitting
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text(
                          'Valider l\'Entrée en Stock',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
