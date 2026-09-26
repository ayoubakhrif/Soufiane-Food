import 'package:flutter/material.dart';
import '../models/agent.dart';
import '../models/pending_operation.dart';
import '../services/api_service.dart';
import '../services/local_storage_service.dart';
import 'login_screen.dart';
import 'stock_entry_screen.dart';
import 'stock_exit_screen.dart';
import 'stock_transfer_screen.dart';
import 'exits_history_screen.dart';
import 'bulk_order_screen.dart';

class HomeScreen extends StatefulWidget {
  final Agent agent;

  const HomeScreen({super.key, required this.agent});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _pendingCount = 0;
  bool _isSyncing = false;

  @override
  void initState() {
    super.initState();
    _checkPendingOperations();
  }

  Future<void> _checkPendingOperations() async {
    final list = await LocalStorageService.getPendingOperations();
    setState(() {
      _pendingCount = list.length;
    });
  }

  Future<void> _triggerSync() async {
    if (_pendingCount == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Aucune opération en attente.')),
      );
      return;
    }

    setState(() => _isSyncing = true);
    final synced = await ApiService.syncPendingOperations();
    await _checkPendingOperations();
    setState(() => _isSyncing = false);

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(' opération(s) synchronisée(s) avec succès !'),
        backgroundColor: Colors.green,
      ),
    );
  }

  void _handleLogout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Déconnexion'),
        content: const Text('Voulez-vous vraiment vous déconnecter ?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Non')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Oui')),
        ],
      ),
    );

    if (confirm == true) {
      await LocalStorageService.clearSession();
      if (!mounted) return;
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const LoginScreen()),
      );
    }
  }

  Widget _buildActionButton({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      width: double.infinity,
      child: Material(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 22),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: Colors.white, size: 30),
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: color.withOpacity(0.95),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        subtitle,
                        style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                      ),
                    ],
                  ),
                ),
                Icon(Icons.arrow_forward_ios, size: 18, color: color.withOpacity(0.6)),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Kal3iya Stock'),
        backgroundColor: Colors.blue.shade900,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Déconnexion',
            onPressed: _handleLogout,
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 500),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Bandeau Agent connecté
                Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [Colors.blue.shade900, Colors.blue.shade700],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: Colors.white.withOpacity(0.2),
                    child: const Icon(Icons.person, color: Colors.white, size: 32),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Agent de terrain',
                          style: TextStyle(color: Colors.white70, fontSize: 12),
                        ),
                        Text(
                          widget.agent.name,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          widget.agent.phone,
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Alerte synchronisation hors-ligne si besoin
            if (_pendingCount > 0)
              Container(
                margin: const EdgeInsets.only(bottom: 16),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.orange.shade300),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.cloud_off, color: Colors.orange),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        ' opération(s) enregistrée(s) hors-ligne.',
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                      ),
                    ),
                    ElevatedButton(
                      onPressed: _isSyncing ? null : _triggerSync,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange.shade800,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      ),
                      child: _isSyncing
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                            )
                          : const Text('Synchroniser', style: TextStyle(fontSize: 12)),
                    ),
                  ],
                ),
              ),

            const Text(
              'Actions Opérationnelles',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 14),

            // 1. Entrée Stock
            _buildActionButton(
              title: 'Entrée en Stock',
              subtitle: 'Réceptionner conteneur, saisir lot, DUM & photos',
              icon: Icons.add_business_rounded,
              color: Colors.green.shade700,
              onTap: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => StockEntryScreen(agent: widget.agent)),
                );
                _checkPendingOperations();
              },
            ),

            // 2. Sortie Stock
            _buildActionButton(
              title: 'Sortie de Stock',
              subtitle: 'Choisir le produit par carte visuelle & affecter au client',
              icon: Icons.local_shipping_rounded,
              color: Colors.red.shade700,
              onTap: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => StockExitScreen(agent: widget.agent)),
                );
                _checkPendingOperations();
              },
            ),

            // 3. Transfert Garage
            _buildActionButton(
              title: 'Transfert entre Garages',
              subtitle: 'Déplacer de la marchandise d\'un garage à un autre',
              icon: Icons.sync_alt_rounded,
              color: Colors.blue.shade800,
              onTap: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => StockTransferScreen(agent: widget.agent)),
                );
                _checkPendingOperations();
              },
            ),

            // 4. Retour Client
            _buildActionButton(
              title: 'Retours Clients',
              subtitle: 'Historique des sorties & déclaration de retours',
              icon: Icons.assignment_return_rounded,
              color: Colors.orange.shade800,
              onTap: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => ExitsHistoryScreen(agent: widget.agent)),
                );
                _checkPendingOperations();
              },
            ),
            // 5. Commande Groupée
            _buildActionButton(
              title: 'Commande Groupée (Tournée)',
              subtitle: 'Assigner plusieurs clients à un chauffeur',
              icon: Icons.map_rounded,
              color: Colors.purple.shade700,
              onTap: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => BulkOrderScreen(agent: widget.agent)),
                );
                _checkPendingOperations();
              },
            ),
          ],
        ),
      ),
    ),
  ),
);
  }
}
