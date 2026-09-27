import codecs

code = r'''import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../services/api_service.dart';
import 'login_screen.dart';

class DriverDashboardScreen extends StatefulWidget {
  final Agent agent;
  const DriverDashboardScreen({super.key, required this.agent});

  @override
  State<DriverDashboardScreen> createState() => _DriverDashboardScreenState();
}

class _DriverDashboardScreenState extends State<DriverDashboardScreen> {
  bool _isLoading = true;
  List<Map<String, dynamic>> _exits = [];
  Map<String, List<Map<String, dynamic>>> _groupedExits = {};

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final exits = await ApiService.fetchDriverExits(widget.agent.id);
      
      final Map<String, List<Map<String, dynamic>>> grouped = {};
      for (var ex in exits) {
        if (ex['state'] == 'delivered') continue;
        final clientName = (ex['client_name'] as String?)?.isNotEmpty == true
            ? ex['client_name'] as String
            : 'Client non défini';
        if (!grouped.containsKey(clientName)) {
          grouped[clientName] = [];
        }
        grouped[clientName]!.add(ex);
      }

      if (!mounted) return;
      setState(() {
        _exits = exits;
        _groupedExits = grouped;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    }
  }

  Future<void> _markClientDelivered(String clientName, List<Map<String, dynamic>> exits) async {
    final exitIds = exits.map((e) => e['id'] as int).toList();
    setState(() => _isLoading = true);
    try {
      final res = await ApiService.markDelivered(exitIds);
      if (!mounted) return;
      if (res['status'] == 'success') {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Livraison confirmée pour $clientName')));
        _loadData();
      } else {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['message'] ?? 'Erreur')));
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    }
  }

  void _showImageDialog(BuildContext context, String title, String imageB64) {
    if (imageB64.isEmpty) return;
    showDialog(
      context: context,
      builder: (_) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),
            ClipRRect(
              borderRadius: const BorderRadius.vertical(bottom: Radius.circular(16)),
              child: Image.memory(
                base64Decode(imageB64),
                fit: BoxFit.contain,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Tournée - ${widget.agent.name}'),
        backgroundColor: Colors.indigo.shade800,
        foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), tooltip: 'Actualiser', onPressed: _loadData),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Déconnexion',
            onPressed: () {
              Navigator.pushReplacement(
                context, 
                MaterialPageRoute(builder: (_) => const LoginScreen())
              );
            },
          )
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _groupedExits.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.check_circle_outline, size: 64, color: Colors.green.shade400),
                      const SizedBox(height: 12),
                      const Text(
                        'Aucune livraison en attente pour aujourd\'hui.',
                        style: TextStyle(fontSize: 16, color: Colors.grey),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  itemCount: _groupedExits.length,
                  itemBuilder: (context, index) {
                    final clientName = _groupedExits.keys.elementAt(index);
                    final clientExits = _groupedExits[clientName]!;
                    final totalQty = clientExits.fold<double>(0.0, (sum, ex) => sum + (double.tryParse(ex['qty'].toString()) ?? 0.0));

                    return Card(
                      elevation: 3,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      margin: const EdgeInsets.symmetric(vertical: 8),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.indigo.shade50,
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: const Icon(Icons.storefront_rounded, color: Colors.indigo, size: 24),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        clientName,
                                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                                      ),
                                      Text(
                                        '${clientExits.length} article(s) • Total: ${totalQty % 1 == 0 ? totalQty.toInt() : totalQty} unités',
                                        style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            const Divider(height: 1),
                            const SizedBox(height: 8),
                            ...clientExits.map((ex) {
                              final imgB64 = (ex['image_b64'] as String?) ?? '';
                              final qtyNum = double.tryParse(ex['qty'].toString()) ?? 0.0;
                              final qtyStr = qtyNum % 1 == 0 ? qtyNum.toInt().toString() : qtyNum.toString();
                              final lot = (ex['lot'] as String?) ?? '';
                              final dum = (ex['dum'] as String?) ?? '';

                              return Padding(
                                padding: const EdgeInsets.symmetric(vertical: 6.0),
                                child: InkWell(
                                  onTap: imgB64.isNotEmpty
                                      ? () => _showImageDialog(context, ex['product_name'] ?? 'Emballage', imgB64)
                                      : null,
                                  borderRadius: BorderRadius.circular(10),
                                  child: Container(
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: Colors.grey.shade50,
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(color: Colors.grey.shade200),
                                    ),
                                    child: Row(
                                      children: [
                                        // Packaging Photo Thumbnail
                                        ClipRRect(
                                          borderRadius: BorderRadius.circular(8),
                                          child: Container(
                                            width: 58,
                                            height: 58,
                                            color: Colors.white,
                                            child: imgB64.isNotEmpty
                                                ? Image.memory(
                                                    base64Decode(imgB64),
                                                    fit: BoxFit.cover,
                                                    errorBuilder: (_, __, ___) => const Icon(
                                                      Icons.inventory_2_outlined,
                                                      size: 28,
                                                      color: Colors.grey,
                                                    ),
                                                  )
                                                : const Icon(
                                                    Icons.inventory_2_outlined,
                                                    size: 28,
                                                    color: Colors.grey,
                                                  ),
                                          ),
                                        ),
                                        const SizedBox(width: 12),
                                        // Product Name & Lot / DUM details
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                ex['product_name'] ?? '',
                                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                                              ),
                                              const SizedBox(height: 2),
                                              Row(
                                                children: [
                                                  if (lot.isNotEmpty) ...[
                                                    Text(
                                                      'Lot: $lot',
                                                      style: TextStyle(color: Colors.grey.shade700, fontSize: 12),
                                                    ),
                                                    const SizedBox(width: 8),
                                                  ],
                                                  if (dum.isNotEmpty)
                                                    Text(
                                                      'DUM: $dum',
                                                      style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                                                    ),
                                                ],
                                              ),
                                            ],
                                          ),
                                        ),
                                        // Quantity Badge
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                          decoration: BoxDecoration(
                                            color: Colors.indigo.shade50,
                                            borderRadius: BorderRadius.circular(8),
                                            border: Border.all(color: Colors.indigo.shade200),
                                          ),
                                          child: Text(
                                            '$qtyStr unités',
                                            style: TextStyle(
                                              fontWeight: FontWeight.bold,
                                              fontSize: 14,
                                              color: Colors.indigo.shade900,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            }),
                            const SizedBox(height: 14),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton.icon(
                                icon: const Icon(Icons.check_circle_rounded),
                                label: const Text('Tout marquer comme Livré', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.green.shade700,
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(vertical: 14),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                ),
                                onPressed: () => _markClientDelivered(clientName, clientExits),
                              ),
                            )
                          ],
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
'''

with codecs.open('gestion_stock_app/lib/screens/driver_dashboard_screen.dart', 'w', encoding='utf-8') as f:
    f.write(code)

print("Driver dashboard updated with images")
