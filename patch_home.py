import codecs

with codecs.open('gestion_stock_app/lib/screens/home_screen.dart', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import
content = content.replace("import 'exits_history_screen.dart';", "import 'exits_history_screen.dart';\nimport 'bulk_order_screen.dart';")

# Add button
old_button = '''            // 4. Retour Client
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
            ),'''
            
new_buttons = old_button + '''
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
            ),'''

content = content.replace(old_button, new_buttons)

with codecs.open('gestion_stock_app/lib/screens/home_screen.dart', 'w', encoding='utf-8') as f:
    f.write(content)
