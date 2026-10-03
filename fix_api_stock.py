import sys

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

# Change action_confirm to action_register in api_exit
content = content.replace(
    "exit_rec = request.env['casa_field.stock.exit'].sudo().create(vals)\n            exit_rec.action_confirm()",
    "exit_rec = request.env['casa_field.stock.exit'].sudo().create(vals)\n            exit_rec.action_register()"
)

# In api_exits
content = content.replace(
    "domain = [('state', '=', 'done')]",
    "domain = [('state', 'in', ['done', 'registered'])]"
)

# In api_commercial_exits_history
content = content.replace(
    "domain = [('state', 'in', ['done', 'delivered'])]",
    "domain = [('state', 'in', ['done', 'delivered', 'registered'])]"
)

# Add api_confirm_exit endpoint
new_api = """

    @http.route('/api/casa/exit/confirm', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_confirm_exit(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_id = int(data.get('exit_id'))
            exit_rec = request.env['casa_field.stock.exit'].sudo().browse(exit_id)
            if not exit_rec.exists():
                return self._json_response({'status': 'error', 'message': 'Sortie introuvable.'}, status=404)
                
            exit_rec.action_confirm()
            return self._json_response({'status': 'success', 'message': 'Sortie confirmée.'})
        except Exception as e:
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)
"""
content = content.replace(
    "    @http.route('/api/casa/return', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')",
    new_api + "\n    @http.route('/api/casa/return', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')"
)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated api_stock.py")
