import sys

with open('custom-addons/stock_casa_field/controllers/api_stock.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "'role': 'agent'",
    "'role': agent.role"
)

endpoints = """
    @http.route('/api/casa/orders/pending_count', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_orders_pending_count(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        count = request.env['casa_field.stock.order'].sudo().search_count([('state', '=', 'pending')])
        return self._json_response({'status': 'success', 'count': count})

    @http.route('/api/casa/orders', type='http', auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False, cors='*')
    def api_orders(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        
        if request.httprequest.method == 'GET':
            orders = request.env['casa_field.stock.order'].sudo().search([('state', '=', 'pending')], order='date desc')
            data = []
            for order in orders:
                lines = []
                for line in order.line_ids:
                    lines.append({
                        'product_id': line.product_id.id,
                        'product_name': line.product_id.name,
                        'quantity': line.quantity,
                        'weight': line.weight,
                        'tonnage': line.tonnage,
                        'note': line.note or ''
                    })
                data.append({
                    'id': order.id,
                    'name': order.name,
                    'date': order.date.strftime('%Y-%m-%d %H:%M:%S'),
                    'commercial_name': order.commercial_id.name,
                    'client_name': order.client_id.name,
                    'lines': lines
                })
            return self._json_response({'status': 'success', 'orders': data})
        
        elif request.httprequest.method == 'POST':
            data = self._get_request_data()
            commercial_id = data.get('commercial_id')
            client_id = data.get('client_id')
            lines = data.get('lines', [])
            
            if not commercial_id or not client_id or not lines:
                return self._json_response({'status': 'error', 'message': 'Invalid data'}, status=400)
                
            order_vals = {
                'commercial_id': commercial_id,
                'client_id': client_id,
                'state': 'pending',
                'line_ids': []
            }
            
            for l in lines:
                order_vals['line_ids'].append((0, 0, {
                    'product_id': l.get('product_id'),
                    'quantity': float(l.get('quantity', 1.0)),
                    'weight': float(l.get('weight', 0.0)),
                    'note': l.get('note', '')
                }))
                
            order = request.env['casa_field.stock.order'].sudo().create(order_vals)
            return self._json_response({'status': 'success', 'message': 'Sent', 'order_id': order.id})

    @http.route('/api/casa/orders/validate', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_orders_validate(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        order_id = data.get('order_id')
        if not order_id:
            return self._json_response({'status': 'error', 'message': 'Order ID missing'}, status=400)
            
        order = request.env['casa_field.stock.order'].sudo().browse(int(order_id))
        if order.exists():
            order.write({'state': 'done'})
            return self._json_response({'status': 'success'})
        return self._json_response({'status': 'error', 'message': 'Order not found'}, status=404)
"""
content = content[:content.rfind('}')] + endpoints + "\n}\n"

with open('custom-addons/stock_casa_field/controllers/api_stock.py', 'w', encoding='utf-8') as f:
    f.write(content)
