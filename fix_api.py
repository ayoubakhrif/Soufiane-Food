import sys

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

new_endpoints = """
    @http.route('/api/casa/commercial/orders_history', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_commercial_orders_history(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
            
        data = self._get_request_data()
        commercial_id = data.get('commercial_id')
        
        domain = []
        if commercial_id:
            domain.append(('commercial_id', '=', int(commercial_id)))
            
        orders = request.env['casa_field.stock.order'].sudo().search(domain, order='date desc, id desc', limit=100)
        
        result = []
        for o in orders:
            lines = []
            for l in o.line_ids:
                lines.append({
                    'product_name': l.product_id.name if l.product_id else '',
                    'quantity': l.quantity,
                    'weight': l.weight,
                    'tonnage': l.tonnage,
                    'note': l.note or ''
                })
            result.append({
                'id': o.id,
                'name': o.name,
                'date': str(o.date),
                'client_name': o.client_id.name if o.client_id else '',
                'state': o.state,
                'lines': lines
            })
            
        return self._json_response({
            'status': 'success',
            'orders': result
        })

    @http.route('/api/casa/commercial/exits_history', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_commercial_exits_history(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
            
        domain = [('state', 'in', ['done', 'delivered'])]
        exits = request.env['casa_field.stock.exit'].sudo().search(domain, order='date desc, id desc', limit=200)
        
        data = []
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        for rec in exits:
            image_url = ""
            if rec.product_id and rec.product_id.image_emballage:
                image_url = f"{base_url}/web/image?model=casa_field.stock.product&id={rec.product_id.id}&field=image_emballage"
                
            data.append({
                'id': rec.id,
                'name': rec.name,
                'date': str(rec.date),
                'product_name': rec.product_id.name if rec.product_id else '',
                'image_url': image_url,
                'client_name': rec.client_id.name if rec.client_id else 'Inconnu',
                'qty': rec.qty,
                'weight': rec.weight,
                'tonnage': rec.tonnage,
                'state': rec.state,
                'driver_name': rec.driver_id.name if rec.driver_id else ''
            })
            
        return self._json_response({
            'status': 'success',
            'exits': data
        })

    @http.route('/api/casa/return', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
"""

content = content.replace("    @http.route('/api/casa/return', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')", new_endpoints)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
