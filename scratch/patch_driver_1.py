import os
import re

repo_dir = r"c:\odoo-repos\Soufiane-Food"
casa_app = os.path.join(repo_dir, "gestion_stock_app_casa")
casa_backend = os.path.join(repo_dir, "custom-addons", "stock_casa_field")

# --- 1. Odoo Backend Updates ---
# 1a. models/casa_field_stock_stock_exit.py
exit_model_path = os.path.join(casa_backend, "models", "casa_field_stock_stock_exit.py")
with open(exit_model_path, "r", encoding="utf-8") as f:
    exit_model_content = f.read()

if "('delivered', 'Livré')" not in exit_model_content:
    exit_model_content = exit_model_content.replace(
        "('done', 'Confirmé'),",
        "('done', 'Confirmé'),\n        ('delivered', 'Livré'),"
    )

if "def action_deliver(self):" not in exit_model_content:
    action_deliver_code = """
    def action_deliver(self):
        for rec in self:
            if rec.state == 'done':
                rec.state = 'delivered'
"""
    exit_model_content += action_deliver_code
    with open(exit_model_path, "w", encoding="utf-8") as f:
        f.write(exit_model_content)

# 1b. controllers/api_stock.py
api_stock_path = os.path.join(casa_backend, "controllers", "api_stock.py")
with open(api_stock_path, "r", encoding="utf-8") as f:
    api_stock_content = f.read()

if "def api_driver_exits" not in api_stock_content:
    new_endpoints = """
    @http.route('/api/casa/driver_exits', type='http', auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False, cors='*')
    def api_driver_exits(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        driver_id = data.get('driver_id')
        if not driver_id:
            return self._json_response({'status': 'error', 'message': 'Chauffeur non specifie'}, status=400)
            
        domain = [('driver_id', '=', int(driver_id)), ('state', 'in', ['done', 'delivered'])]
        exits = request.env['casa_field.stock.exit'].sudo().search(domain, order='date desc, id desc')
        
        result = []
        for rec in exits:
            image_b64 = ''
            if rec.product_id:
                entry = request.env['casa_field.stock.entry'].sudo().search([
                    ('product_id', '=', rec.product_id.id),
                    ('lot', '=', rec.lot),
                    ('photo_packaging', '!=', False)
                ], limit=1, order='date desc, id desc')

                if entry and entry.photo_packaging:
                    image_b64 = entry.photo_packaging.decode('utf-8') if isinstance(entry.photo_packaging, bytes) else str(entry.photo_packaging)
                elif rec.product_id.image_1920:
                    img = rec.product_id.image_1920
                    image_b64 = img.decode('utf-8') if isinstance(img, bytes) else str(img)

            result.append({
                'id': rec.id,
                'name': rec.name,
                'date': str(rec.date),
                'product_name': rec.product_id.name if rec.product_id else '',
                'lot': rec.lot or '',
                'dum': rec.dum or '',
                'qty': rec.qty,
                'client_id': rec.client_id.id if rec.client_id else None,
                'client_name': rec.client_id.name if rec.client_id else '',
                'state': rec.state,
                'order_reference': rec.order_reference or '',
                'image_b64': image_b64,
            })
        return self._json_response({'status': 'success', 'exits': result})

    @http.route('/api/casa/mark_delivered', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_mark_delivered(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_ids = data.get('exit_ids', [])
            if not exit_ids:
                return self._json_response({'status': 'error', 'message': 'Aucune sortie specifiee'}, status=400)
                
            exits = request.env['casa_field.stock.exit'].sudo().browse(exit_ids)
            exits.action_deliver()
            
            return self._json_response({'status': 'success', 'message': 'Mise a jour reussie'})
        except Exception as e:
            _logger.exception("Erreur API Mark Delivered")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)
"""
    api_stock_content += new_endpoints
    with open(api_stock_path, "w", encoding="utf-8") as f:
        f.write(api_stock_content)

# --- 2. Flutter App Updates ---

# 2a. Update agent.dart
agent_dart_path = os.path.join(casa_app, "lib", "models", "agent.dart")
with open(agent_dart_path, "r", encoding="utf-8") as f:
    agent_dart_content = f.read()

if "final String role;" not in agent_dart_content:
    agent_dart_content = agent_dart_content.replace(
        "final String phone;",
        "final String phone;\n  final String role;"
    ).replace(
        "required this.phone,",
        "required this.phone,\n    required this.role,"
    ).replace(
        "phone: json['phone'] as String? ?? '',",
        "phone: json['phone'] as String? ?? '',\n      role: json['role'] as String? ?? 'agent',"
    ).replace(
        "'phone': phone,",
        "'phone': phone,\n    'role': role,"
    )
    with open(agent_dart_path, "w", encoding="utf-8") as f:
        f.write(agent_dart_content)


# 2b. Update api_service.dart
api_service_path = os.path.join(casa_app, "lib", "services", "api_service.dart")
with open(api_service_path, "r", encoding="utf-8") as f:
    api_service_content = f.read()

if "fetchDriverExits" not in api_service_content:
    new_api_methods = """
  static Future<List<Map<String, dynamic>>> fetchDriverExits(int driverId) async {
    final uri = Uri.parse('$baseUrl/api/casa/driver_exits');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'driver_id': driverId}));
    final data = jsonDecode(response.body);
    if (data['status'] == 'success') {
      return List<Map<String, dynamic>>.from(data['exits']);
    } else {
      throw Exception(data['message'] ?? 'Erreur');
    }
  }

  static Future<Map<String, dynamic>> markDelivered(List<int> exitIds) async {
    final uri = Uri.parse('$baseUrl/api/casa/mark_delivered');
    final response = await http.post(uri, headers: _headers, body: jsonEncode({'exit_ids': exitIds}));
    return jsonDecode(response.body);
  }
"""
    api_service_content = api_service_content.replace("\n}\n", new_api_methods + "\n}\n")
    with open(api_service_path, "w", encoding="utf-8") as f:
        f.write(api_service_content)

# 2c. Update login_screen.dart
login_screen_path = os.path.join(casa_app, "lib", "screens", "login_screen.dart")
with open(login_screen_path, "r", encoding="utf-8") as f:
    login_screen_content = f.read()

if "DriverDashboardScreen" not in login_screen_content:
    login_screen_content = login_screen_content.replace(
        "import 'home_screen.dart';",
        "import 'home_screen.dart';\nimport 'driver_dashboard_screen.dart';"
    ).replace(
        "MaterialPageRoute(builder: (_) => HomeScreen(agent: agent)),",
        "MaterialPageRoute(builder: (_) => agent.role == 'driver' ? DriverDashboardScreen(agent: agent) : HomeScreen(agent: agent)),"
    )
    with open(login_screen_path, "w", encoding="utf-8") as f:
        f.write(login_screen_content)

print("Patch generated successfully")
