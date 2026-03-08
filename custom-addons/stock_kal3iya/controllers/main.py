from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class StockKal3iyaController(http.Controller):

    @http.route('/api/stock_kal3iya/validate', type='http', auth='public', methods=['POST'], csrf=False)
    def validate_stock(self, **post):
        # 1. Security Check (Token)
        expected_token = request.env['ir.config_parameter'].sudo().get_param('stock_kal3iya.api_token')
        auth_header = request.httprequest.headers.get('Authorization')
        
        # If no token configured, block everything for safety
        if not expected_token:
            _logger.warning("API Validation attempted but 'stock_kal3iya.api_token' is not set.")
            return request.make_response(
                json.dumps({'valid': False, 'error': 'Server configuration error (Token)'}),
                headers={'Content-Type': 'application/json'},
                status=500
            )

        if auth_header != f"Bearer {expected_token}":
             return request.make_response(
                json.dumps({'valid': False, 'error': 'Unauthorized'}),
                headers={'Content-Type': 'application/json'},
                status=401
            )

        # 2. Parse Body
        try:
            data = json.loads(request.httprequest.data)
        except Exception as e:
             return request.make_response(
                json.dumps({'valid': False, 'error': 'Invalid JSON format'}),
                headers={'Content-Type': 'application/json'},
                status=400
            )

        items = data.get('items', [])
        if not items:
             return request.make_response(
                json.dumps({'valid': False, 'error': 'No items provided'}),
                headers={'Content-Type': 'application/json'},
                status=400
            )

        errors = []
        Stock = request.env['stock.kal3iya.stock'].sudo()

        # 3. Process Items
        for item in items:
            product_name = item.get('product')
            lot = item.get('lot')
            garage = item.get('garage')
            qty = item.get('quantity', 1)

            if not product_name or not lot or not garage:
                errors.append({
                    'product': product_name,
                    'lot': lot,
                    'error': 'Missing required fields (product, lot, garage)'
                })
                continue

            record = Stock.search([
                ('product_id.name', '=', product_name),
                ('lot', '=', lot),
                ('garage', '=', garage),
            ], limit=1)

            if not record:
                errors.append({
                    'product': product_name,
                    'lot': lot,
                    'error': 'Product / Lot / Garage combination does not exist'
                })
                continue



        # 4. Response
        if not errors:
            return request.make_response(
                json.dumps({
                    'valid': True, 
                    'message': 'All items are valid'
                }),
                headers={'Content-Type': 'application/json'}
            )

        else:
            return request.make_response(
                json.dumps({
                    'valid': False, 
                    'errors': errors
                }),
                headers={'Content-Type': 'application/json'}
            )

    @http.route('/api/stock_kal3iya/snapshot', type='http', auth='public', methods=['POST'], csrf=False)
    def snapshot_stock(self, **post):
        # 1. Security Check (Token)
        expected_token = request.env['ir.config_parameter'].sudo().get_param('stock_kal3iya.api_token')
        auth_header = request.httprequest.headers.get('Authorization')
        
        # If no token configured, block everything for safety
        if not expected_token:
            _logger.warning("API Snapshot attempted but 'stock_kal3iya.api_token' is not set.")
            return request.make_response(
                json.dumps({'error': 'Server configuration error (Token)'}),
                headers={'Content-Type': 'application/json'},
                status=500
            )

        if auth_header != f"Bearer {expected_token}":
             return request.make_response(
                json.dumps({'error': 'Unauthorized'}),
                headers={'Content-Type': 'application/json'},
                status=401
            )

        # 2. Logic - Fetch Snapshot
        Stock = request.env['stock.kal3iya.stock'].sudo()
        
        # Fetch all records from the view
        records = Stock.search_read(
            [('quantity', '>', 0)],
            ['product_id', 'lot', 'garage']
        )
        
        # Deduplicate by (product_id, lot, garage)
        unique_keys = set()
        products_list = []
        
        for rec in records:
            # product_id is (id, name) in search_read result for Many2one
            p_id = rec['product_id'][0] if rec['product_id'] else False
            p_name = rec['product_id'][1] if rec['product_id'] else ""
            lot = rec['lot'] or ""
            garage = rec['garage'] or "" 
            
            key = (p_id, lot, garage)
            
            if key not in unique_keys:
                unique_keys.add(key)
                products_list.append({
                    'product_id': p_id,
                    'product_name': p_name,
                    'lot': lot,
                    'garage': garage
                })
        
        return request.make_response(
            json.dumps({'products': products_list}),
            headers={'Content-Type': 'application/json'}
        )

    @http.route('/api/stock_kal3iya/chat', type='http', auth='public', methods=['POST'], csrf=False)
    def chat(self, **post):
        """WhatsApp chatbot endpoint. Receives a message, returns a stock-related answer."""
        # 1. Security Check (Token)
        expected_token = request.env['ir.config_parameter'].sudo().get_param('stock_kal3iya.api_token')
        auth_header = request.httprequest.headers.get('Authorization')

        if not expected_token:
            _logger.warning("Chat API attempted but 'stock_kal3iya.api_token' is not set.")
            return request.make_response(
                json.dumps({'error': 'Server configuration error (Token)'}),
                headers={'Content-Type': 'application/json'},
                status=500
            )

        if auth_header != f"Bearer {expected_token}":
            return request.make_response(
                json.dumps({'error': 'Unauthorized'}),
                headers={'Content-Type': 'application/json'},
                status=401
            )

        # 2. Parse Body
        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            return request.make_response(
                json.dumps({'error': 'Invalid JSON format'}),
                headers={'Content-Type': 'application/json'},
                status=400
            )

        message = data.get('message', '').strip()
        sender = data.get('sender', 'unknown')

        if not message:
            return request.make_response(
                json.dumps({'error': 'No message provided'}),
                headers={'Content-Type': 'application/json'},
                status=400
            )

        # 3. Process via Chatbot Engine
        try:
            Chatbot = request.env['stock.kal3iya.chatbot'].sudo()
            response_text = Chatbot.process_message(message, sender=sender)
        except Exception as e:
            _logger.error("Chatbot processing error: %s", str(e))
            response_text = "Erreur interne. Veuillez réessayer."

        # 4. Return Response
        return request.make_response(
            json.dumps({'response': response_text}),
            headers={'Content-Type': 'application/json'}
        )
