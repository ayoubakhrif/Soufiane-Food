import codecs
import re

with codecs.open('custom-addons/kal3iya_stock/controllers/api_stock.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_login = False
for line in lines:
    if 'agent = request.env[' in line and 'kal3iya.stock.agent' in line and 'api_login' not in line: # start of auth block
        in_login = True
        new_lines.append('''        agent = request.env['kal3iya.stock.agent'].sudo().search([('phone', '=', phone), ('active', '=', True)], limit=1)
        if agent and agent.password == password:
            return self._json_response({'status': 'success', 'agent': {'id': agent.id, 'name': agent.name, 'phone': agent.phone, 'role': 'agent'}})
            
        driver = request.env['kal3iya.stock.driver'].sudo().search([('phone', '=', phone)], limit=1)
        if driver and driver.password == password:
            return self._json_response({'status': 'success', 'agent': {'id': driver.id, 'name': driver.name, 'phone': driver.phone, 'role': 'driver'}})

        return self._json_response({'status': 'error', 'message': 'Numero de telephone ou mot de passe incorrect.'}, status=401)
''')
    elif in_login:
        if 'def api_bootstrap' in line:
            in_login = False
            new_lines.append(line)
    else:
        new_lines.append(line)

content = "".join(new_lines)

# Append new routes
content += '''
    @http.route('/api/kal3iya/bulk_exit', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
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
                    'garage': line.get('garage'),
                    'frigo': line.get('frigo') or 'stock_kal3iya',
                    'lot': line.get('lot') or '',
                    'qty': float(line.get('qty', 0)),
                    'date': self._sanitize_date(line.get('date')),
                    'driver_id': driver_id,
                    'order_reference': order_ref,
                }
                exit_rec = request.env['kal3iya.stock.exit'].sudo().create(vals)
                exit_rec.action_confirm()
                created_exits.append(exit_rec.id)

            return self._json_response({'status': 'success', 'message': f'{len(created_exits)} sorties crées avec succès.'})
        except Exception as e:
            _logger.exception("Erreur API Bulk Exit")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route('/api/kal3iya/driver_exits', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_driver_exits(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        driver_id = data.get('driver_id')
        if not driver_id:
            return self._json_response({'status': 'error', 'message': 'Chauffeur non specifie'}, status=400)
            
        domain = [('driver_id', '=', int(driver_id)), ('state', 'in', ['done', 'delivered'])]
        exits = request.env['kal3iya.stock.exit'].sudo().search(domain, order='date desc, id desc')
        
        result = []
        for rec in exits:
            result.append({
                'id': rec.id,
                'name': rec.name,
                'date': str(rec.date),
                'product_name': rec.product_id.name if rec.product_id else '',
                'lot': rec.lot or '',
                'qty': rec.qty,
                'client_id': rec.client_id.id if rec.client_id else None,
                'client_name': rec.client_id.name if rec.client_id else '',
                'state': rec.state,
                'order_reference': rec.order_reference or '',
            })
        return self._json_response({'status': 'success', 'exits': result})

    @http.route('/api/kal3iya/mark_delivered', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_mark_delivered(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_ids = data.get('exit_ids', [])
            if not exit_ids:
                return self._json_response({'status': 'error', 'message': 'Aucune sortie specifiee'}, status=400)
                
            exits = request.env['kal3iya.stock.exit'].sudo().browse(exit_ids)
            exits.action_deliver()
            
            return self._json_response({'status': 'success', 'message': 'Mise a jour reussie'})
        except Exception as e:
            _logger.exception("Erreur API Mark Delivered")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)
'''

with codecs.open('custom-addons/kal3iya_stock/controllers/api_stock.py', 'w', encoding='utf-8') as f:
    f.write(content)
