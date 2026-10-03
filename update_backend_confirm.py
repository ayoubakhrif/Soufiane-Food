import sys

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

new_api = """

    @http.route('/api/casa/exit/confirm', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_confirm_exit(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_id = int(data.get('exit_id'))
            driver_id = data.get('driver_id')
            exit_rec = request.env['casa_field.stock.exit'].sudo().browse(exit_id)
            if not exit_rec.exists():
                return self._json_response({'status': 'error', 'message': 'Sortie introuvable.'}, status=404)
            
            if driver_id:
                exit_rec.write({'driver_id': int(driver_id)})
                
            exit_rec.action_confirm()
            return self._json_response({'status': 'success', 'message': 'Sortie confirmée.'})
        except Exception as e:
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)
"""

# Replace the old api_confirm_exit definition
import re
pattern = r"@http\.route\('/api/casa/exit/confirm'.*?def api_confirm_exit\(self, \*\*kwargs\):.*?except Exception as e:\n.*?return self\._json_response\(\{'status': 'error', 'message': str\(e\)\}, status=500\)"
content = re.sub(pattern, new_api.strip(), content, flags=re.DOTALL)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated api_stock.py")
