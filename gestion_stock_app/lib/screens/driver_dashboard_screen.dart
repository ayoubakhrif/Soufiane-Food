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
        if (ex['state'] == 'delivered') continue; // Optionally hide delivered, or keep them marked
        final clientName = ex['client_name'] as String;
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
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['message'])));
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Tournée - ${widget.agent.name}'),
        backgroundColor: Colors.indigo,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () {
              // Clear local session if needed here, or just navigate
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
              ? const Center(child: Text('Aucune livraison en attente pour aujourd\'hui.'))
              : ListView.builder(
                  padding: const EdgeInsets.all(8),
                  itemCount: _groupedExits.length,
                  itemBuilder: (context, index) {
                    final clientName = _groupedExits.keys.elementAt(index);
                    final clientExits = _groupedExits[clientName]!;

                    return Card(
                      elevation: 4,
                      margin: const EdgeInsets.symmetric(vertical: 8),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.store, color: Colors.indigo, size: 28),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    clientName,
                                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ),
                            const Divider(),
                            ...clientExits.map((ex) => Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 4.0),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Expanded(
                                        child: Text(
                                          '📦 ${ex['product_name']} ',
                                          style: const TextStyle(fontSize: 16),
                                        ),
                                      ),
                                      Text(
                                        '${ex['qty']} Kg/Unité',
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                                      )
                                    ],
                                  ),
                                )),
                            const SizedBox(height: 16),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton.icon(
                                icon: const Icon(Icons.check_circle),
                                label: const Text('Tout marquer comme Livré'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.green,
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(vertical: 12),
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
