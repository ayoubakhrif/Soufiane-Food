import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/item_models.dart';
import '../services/api_service.dart';

class ExitsHistoryScreen extends StatefulWidget {
  final Agent agent;
  const ExitsHistoryScreen({super.key, required this.agent});

  @override
  State<ExitsHistoryScreen> createState() => _ExitsHistoryScreenState();
}

class _ExitsHistoryScreenState extends State<ExitsHistoryScreen> {
  List<Map<String, dynamic>> _exits = [];
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
      final exits = await ApiService.fetchExits();
      final bootstrap = await ApiService.fetchBootstrap();
      
      if (!mounted) return;
      setState(() {
        _exits = exits;
        _garages = bootstrap['garages'] as List<GarageItem>;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur: $e')),
      );
    }
  }

  void _showReturnDialog(Map<String, dynamic> exitData) {
    double qtyToReturn = 0;
    GarageItem? selectedGarage;
    
    // Default to today
    final String todayDate = DateTime.now().toIso8601String().split('T')[0];

    final double maxReturnable = (exitData['qty'] as num).toDouble() - (exitData['returned_qty'] as num).toDouble();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: Text('Retourner: ${exitData['name']}'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('Produit: ${exitData['product_name']}'),
                    Text('Lot: ${exitData['lot']}'),
                    Text('Client: ${exitData['client_name']}'),
                    Text('Quantité livrée: ${exitData['qty']} (Déjà retourné: ${exitData['returned_qty']})'),
                    const SizedBox(height: 16),
                    TextFormField(
                      initialValue: '0',
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Quantité à retourner',
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (val) {
                        qtyToReturn = double.tryParse(val) ?? 0;
                      },
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<GarageItem>(
                      decoration: const InputDecoration(
                        labelText: 'Garage de destination',
                        border: OutlineInputBorder(),
                      ),
                      value: selectedGarage,
                      items: _garages.map((g) {
                        return DropdownMenuItem(
                          value: g,
                          child: Text(g.label),
                        );
                      }).toList(),
                      onChanged: (val) {
                        setDialogState(() {
                          selectedGarage = val;
                        });
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Annuler'),
                ),
                ElevatedButton(
                  onPressed: () async {
                    if (qtyToReturn <= 0 || qtyToReturn > maxReturnable) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Quantité invalide.')),
                      );
                      return;
                    }
                    if (selectedGarage == null) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Veuillez sélectionner un garage.')),
                      );
                      return;
                    }

                    Navigator.pop(context); // Close dialog
                    _processReturn(exitData['id'], qtyToReturn, selectedGarage!.key, todayDate);
                  },
                  child: const Text('Valider Retour'),
                ),
              ],
            );
          }
        );
      },
    );
  }

  Future<void> _processReturn(int exitId, double qty, String garage, String date) async {
    setState(() => _isLoading = true);
    try {
      final payload = {
        'exit_id': exitId,
        'qty': qty,
        'garage': garage,
        'date': date,
        'driver_id': widget.agent.id, // using agent as driver or we leave empty if not needed
      };
      
      final res = await ApiService.createReturn(payload);
      if (!mounted) return;
      if (res['status'] == 'success') {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(res['message'] ?? 'Retour enregistré avec succès.')),
        );
        _loadData(); // reload list
      } else {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erreur: ${res['message']}')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Historique des Sorties'),
        backgroundColor: Colors.teal,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _exits.isEmpty
              ? const Center(child: Text('Aucune sortie trouvée.'))
              : ListView.builder(
                  padding: const EdgeInsets.all(8),
                  itemCount: _exits.length,
                  itemBuilder: (context, index) {
                    final exitData = _exits[index];
                    final double qty = (exitData['qty'] as num).toDouble();
                    final double returnedQty = (exitData['returned_qty'] as num).toDouble();
                    final double remaining = qty - returnedQty;

                    return Card(
                      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                      child: ListTile(
                        title: Text('${exitData['name']} - ${exitData['product_name']}'),
                        subtitle: Text(
                          'Date: ${exitData['date']}\nClient: ${exitData['client_name']}\nGarage: ${exitData['garage']}\nQte: ${exitData['qty']} (Retourné: $returnedQty)',
                        ),
                        isThreeLine: true,
                        trailing: remaining > 0
                            ? IconButton(
                                icon: const Icon(Icons.assignment_return, color: Colors.teal),
                                onPressed: () => _showReturnDialog(exitData),
                                tooltip: 'Faire un retour',
                              )
                            : const Icon(Icons.check_circle, color: Colors.grey),
                      ),
                    );
                  },
                ),
    );
  }
}
