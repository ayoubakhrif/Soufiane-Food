import os
import re
import shutil

repo_dir = r"c:\odoo-repos\Soufiane-Food"
kal3iya_app = os.path.join(repo_dir, "gestion_stock_app")
casa_app = os.path.join(repo_dir, "gestion_stock_app_casa")
casa_backend = os.path.join(repo_dir, "custom-addons", "stock_casa_field")

# --- 1. Odoo Backend Updates ---
# 1a. models/casa_field_stock_stock_exit.py
exit_model_path = os.path.join(casa_backend, "models", "casa_field_stock_stock_exit.py")
with open(exit_model_path, "r", encoding="utf-8") as f:
    exit_model_content = f.read()

if "order_reference = fields.Char" not in exit_model_content:
    exit_model_content = exit_model_content.replace(
        "name = fields.Char(string='Référence', readonly=True, default='/')",
        "name = fields.Char(string='Référence', readonly=True, default='/')\n    order_reference = fields.Char(string='Référence Commande')"
    )
    with open(exit_model_path, "w", encoding="utf-8") as f:
        f.write(exit_model_content)

# 1b. controllers/api_stock.py
api_stock_path = os.path.join(casa_backend, "controllers", "api_stock.py")
with open(api_stock_path, "r", encoding="utf-8") as f:
    api_stock_content = f.read()

if "def api_bulk_exit" not in api_stock_content:
    new_endpoints = """
    @http.route('/api/casa/bulk_exit', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_bulk_exit(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            driver_id = int(data.get('driver_id')) if data.get('driver_id') else False
            order_ref = data.get('order_reference', '')
            lines = data.get('lines', [])
            
            created_exits = []
            for line in lines:
                vals = {
                    'product_id': int(line.get('product_id')),
                    'client_id': int(line.get('client_id')) if line.get('client_id') else False,
                    'frigo': line.get('frigo') or 'stock_casa',
                    'lot': line.get('lot') or '',
                    'dum': line.get('dum') or '',
                    'qty': float(line.get('qty', 0)),
                    'date': self._sanitize_date(line.get('date')),
                    'driver_id': driver_id,
                    'order_reference': order_ref,
                }
                exit_rec = request.env['casa_field.stock.exit'].sudo().create(vals)
                exit_rec.action_confirm()
                created_exits.append(exit_rec.id)

            return self._json_response({'status': 'success', 'message': f'{len(created_exits)} sorties crées avec succès.'})
        except Exception as e:
            _logger.exception("Erreur API Bulk Exit")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route('/api/casa/exits', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_exits(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        domain = [('state', '=', 'done')]
        exits = request.env['casa_field.stock.exit'].sudo().search(domain, order='date desc, id desc', limit=100)
        data = []
        for rec in exits:
            returned_qty = sum(r.qty for r in rec.return_ids if r.state == 'done')
            if returned_qty < rec.qty: # Only send exits that can still be returned
                data.append({
                    'id': rec.id,
                    'name': rec.name,
                    'date': str(rec.date),
                    'product_name': rec.product_id.name if rec.product_id else '',
                    'lot': rec.lot or '',
                    'client_name': rec.client_id.name if rec.client_id else '',
                    'qty': rec.qty,
                    'returned_qty': returned_qty,
                })

        return self._json_response({
            'status': 'success',
            'exits': data,
        })

    @http.route('/api/casa/return', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_return(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_id = int(data.get('exit_id'))
            exit_rec = request.env['casa_field.stock.exit'].sudo().browse(exit_id)
            if not exit_rec.exists():
                return self._json_response({'status': 'error', 'message': 'Sortie introuvable.'}, status=404)

            vals = {
                'exit_id': exit_id,
                'qty': float(data.get('qty', 0)),
                'date': self._sanitize_date(data.get('date')),
            }

            ret_rec = request.env['casa_field.stock.return'].sudo().create(vals)
            ret_rec.action_confirm()

            return self._json_response({
                'status': 'success',
                'return_id': ret_rec.id,
                'name': ret_rec.name,
                'message': f'Retour {ret_rec.name} enregistré avec succès.'
            })
        except Exception as e:
            _logger.exception('Erreur API Return')
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)
"""
    api_stock_content += new_endpoints
    with open(api_stock_path, "w", encoding="utf-8") as f:
        f.write(api_stock_content)


# --- 2. Flutter Frontend Updates ---
# 2a. Update api_service.dart
api_service_path = os.path.join(casa_app, "lib", "services", "api_service.dart")
with open(api_service_path, "r", encoding="utf-8") as f:
    api_service_content = f.read()

if "createBulkExit" not in api_service_content:
    new_methods = """
  static Future<Map<String, dynamic>> createBulkExit(Map<String, dynamic> payload) async {
    final uri = Uri.parse('$baseUrl/api/casa/bulk_exit');
    final response = await http.post(uri, headers: _headers, body: jsonEncode(payload));
    return jsonDecode(response.body);
  }

  static Future<List<Map<String, dynamic>>> fetchExits() async {
    final uri = Uri.parse('$baseUrl/api/casa/exits');
    final response = await http.get(uri, headers: _headers);
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['exits']);
    } else {
      throw Exception(data['message'] ?? 'Erreur lors de la récupération des sorties');
    }
  }

  static Future<Map<String, dynamic>> createReturn(Map<String, dynamic> payload) async {
    final uri = Uri.parse('$baseUrl/api/casa/return');
    http.Response response;
    try {
      response = await http.post(
        uri,
        headers: _headers,
        body: jsonEncode(payload),
      );
    } catch (e) {
      throw Exception('Erreur réseau. Impossible de contacter le serveur.');
    }

    try {
      final data = jsonDecode(response.body);
      if (response.statusCode == 200 && data['status'] == 'success') {
        return data;
      } else {
        return {
          'status': 'error',
          'message': data['message'] ?? 'Erreur (Code: ${response.statusCode})'
        };
      }
    } catch (_) {
      return {
        'status': 'error',
        'message': 'Erreur serveur (${response.statusCode}): ${response.body}'
      };
    }
  }
"""
    api_service_content = api_service_content.replace("\n}\n", new_methods + "\n}\n")
    with open(api_service_path, "w", encoding="utf-8") as f:
        f.write(api_service_content)

# 2b. Copy bulk_order_screen.dart to stock_exit_screen.dart and adapt
bulk_order_src = os.path.join(kal3iya_app, "lib", "screens", "bulk_order_screen.dart")
stock_exit_dst = os.path.join(casa_app, "lib", "screens", "stock_exit_screen.dart")

with open(bulk_order_src, "r", encoding="utf-8") as f:
    content = f.read()

# Rename BulkOrderScreen to StockExitScreen
content = content.replace("BulkOrderScreen", "StockExitScreen")
content = content.replace("_BulkOrderScreenState", "_StockExitScreenState")

# Remove Garage concepts
content = re.sub(r"List<GarageItem>\s*_garages\s*=\s*\[\];", "", content)
content = re.sub(r"GarageItem\?\s*_selectedGarage;", "", content)
content = re.sub(r"_garages\s*=\s*bootstrap\['garages'\];", "", content)

# Filter stock purely by quantity > 0 instead of checking selectedGarage
content = content.replace(
    "if (_selectedGarage == null) return [];\n    return _allStock.where((s) => s.garage == _selectedGarage!.key && s.quantity > 0).toList();",
    "return _allStock.where((s) => s.quantity > 0).toList();"
)

# Remove Garage from UI
content = re.sub(r"DropdownButtonFormField<GarageItem>\([\s\S]*?onChanged: \(val\) => setState\(\(\) => _selectedGarage = val\),\s*\),", "", content)

# Remove Garage from the condition that checks _selectedGarage == null
content = re.sub(r"_selectedGarage == null\s*\?.*?:\s*filtered\.isEmpty", "filtered.isEmpty", content, flags=re.DOTALL)
content = re.sub(r"DropdownButtonFormField<GarageItem>.*?onChanged.*?,", "", content, flags=re.DOTALL)

# Also remove garage from the api payload
content = re.sub(r"'garage':\s*line\.stock\.garage,", "", content)
# And from the printed cart item
content = re.sub(r" \| Garage: \$\{line\.stock\.garage\}", "", content)

with open(stock_exit_dst, "w", encoding="utf-8") as f:
    f.write(content)

# 2c. Copy exits_history_screen.dart to exits_history_screen.dart and adapt
history_src = os.path.join(kal3iya_app, "lib", "screens", "exits_history_screen.dart")
history_dst = os.path.join(casa_app, "lib", "screens", "exits_history_screen.dart")

with open(history_src, "r", encoding="utf-8") as f:
    hcontent = f.read()

hcontent = re.sub(r"List<GarageItem>\s*_garages\s*=\s*\[\];", "", hcontent)
hcontent = re.sub(r"_garages\s*=\s*bootstrap\['garages'\] as List<GarageItem>;", "", hcontent)
hcontent = re.sub(r"GarageItem\?\s*selectedGarage;", "", hcontent)
hcontent = re.sub(r"DropdownButtonFormField<GarageItem>\([\s\S]*?onChanged: \(val\).*?\}\),\s*\),\s*\}\),\s*\),", "", hcontent)

hcontent = hcontent.replace(
    "_processReturn(exitData['id'], qtyToReturn, selectedGarage!.key, todayDate);",
    "_processReturn(exitData['id'], qtyToReturn, todayDate);"
)
hcontent = hcontent.replace(
    "if (selectedGarage == null) {\n                      ScaffoldMessenger.of(context).showSnackBar(\n                        const SnackBar(content: Text('Veuillez sélectionner un garage.')),\n                      );\n                      return;\n                    }",
    ""
)
hcontent = hcontent.replace(
    "Future<void> _processReturn(int exitId, double qty, String garage, String date) async {",
    "Future<void> _processReturn(int exitId, double qty, String date) async {"
)
hcontent = re.sub(r"'garage':\s*garage,", "", hcontent)
hcontent = re.sub(r"\\nGarage: \$\{exitData\['garage'\]\}", "", hcontent)

# There is a nested DropdownButtonFormField that might not be fully caught by the regex. Let's do a more robust string replacement for it.
hcontent = re.sub(r"DropdownButtonFormField<GarageItem>\([\s\S]*?onChanged: \(val\) \{\s*setDialogState\(\(\) \{\s*selectedGarage = val;\s*\}\);\s*\},\s*\),", "", hcontent)


with open(history_dst, "w", encoding="utf-8") as f:
    f.write(hcontent)

# 2d. Update home_screen.dart to include Retours
home_screen_path = os.path.join(casa_app, "lib", "screens", "home_screen.dart")
with open(home_screen_path, "r", encoding="utf-8") as f:
    home_content = f.read()

if "import 'exits_history_screen.dart';" not in home_content:
    home_content = home_content.replace("import 'stock_exit_screen.dart';", "import 'stock_exit_screen.dart';\nimport 'exits_history_screen.dart';")

if "Retours Clients" not in home_content:
    retour_button = """
            // 3. Retours
            _buildActionButton(
              title: 'Retours Clients',
              subtitle: 'Historique des sorties et retours de marchandise',
              icon: Icons.assignment_return_rounded,
              color: Colors.orange.shade700,
              onTap: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => ExitsHistoryScreen(agent: widget.agent)),
                );
                _checkPendingOperations();
              },
            ),
"""
    home_content = home_content.replace("          ],\n        ),\n      ),\n    ),\n  ),\n);\n  }\n}", retour_button + "          ],\n        ),\n      ),\n    ),\n  ),\n);\n  }\n}")
    with open(home_screen_path, "w", encoding="utf-8") as f:
        f.write(home_content)

print("Patching complete.")
