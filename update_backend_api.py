import sys
import re

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Modify api_bulk_exit to return exit_ids
content = content.replace(
    "return self._json_response({'status': 'success', 'message': f'{len(created_exits)} sorties crees avec succes.'})",
    "return self._json_response({'status': 'success', 'message': f'{len(created_exits)} sorties crees avec succes.', 'exit_ids': created_exits})"
)

# 2. Add driver_name, weight, tonnage to api_exits
content = content.replace(
    "'driver_name': rec.driver_id.name if rec.driver_id else 'Pas de chauffeur',",
    "'driver_name': rec.driver_id.name if rec.driver_id else 'Pas de chauffeur',\n                    'weight': rec.weight,\n                    'tonnage': rec.tonnage,"
)

# 3. Rewrite api_confirm_exit
old_confirm = """    def api_confirm_exit(self, **kwargs):
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
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)"""

new_confirm = """    def api_confirm_exit(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_id = int(data.get('exit_id'))
            driver_id = data.get('driver_id')
            confirm_qty = data.get('qty')
            exit_rec = request.env['casa_field.stock.exit'].sudo().browse(exit_id)
            if not exit_rec.exists():
                return self._json_response({'status': 'error', 'message': 'Sortie introuvable.'}, status=404)
            
            if confirm_qty:
                confirm_qty = float(confirm_qty)
                if confirm_qty < exit_rec.qty:
                    # Create backorder
                    backorder = exit_rec.copy({'qty': exit_rec.qty - confirm_qty, 'state': 'draft', 'move_id': False})
                    backorder.action_register()
                    # Update current exit
                    exit_rec.write({'qty': confirm_qty})
                    if exit_rec.move_id:
                        exit_rec.move_id.write({'qty': -confirm_qty})
            
            if driver_id:
                exit_rec.write({'driver_id': int(driver_id)})
                
            exit_rec.action_confirm()
            return self._json_response({'status': 'success', 'message': 'Sortie confirmée.'})
        except Exception as e:
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route('/api/casa/exit/deliver', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_deliver_exit(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_id = int(data.get('exit_id'))
            exit_rec = request.env['casa_field.stock.exit'].sudo().browse(exit_id)
            if not exit_rec.exists():
                return self._json_response({'status': 'error', 'message': 'Sortie introuvable.'}, status=404)
            
            exit_rec.action_deliver()
            return self._json_response({'status': 'success', 'message': 'Sortie livrée.'})
        except Exception as e:
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route('/api/casa/exit/bulk_confirm', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_bulk_confirm_exit(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_ids = data.get('exit_ids', [])
            driver_id = data.get('driver_id')
            if not exit_ids:
                return self._json_response({'status': 'error', 'message': 'Aucune sortie fournie.'}, status=400)
            
            for eid in exit_ids:
                exit_rec = request.env['casa_field.stock.exit'].sudo().browse(int(eid))
                if exit_rec.exists() and exit_rec.state == 'registered':
                    if driver_id:
                        exit_rec.write({'driver_id': int(driver_id)})
                    exit_rec.action_confirm()
            return self._json_response({'status': 'success', 'message': 'Tournée confirmée.'})
        except Exception as e:
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)"""

content = content.replace(old_confirm, new_confirm)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated backend API for partial exits, bulk confirm, and deliver.")
