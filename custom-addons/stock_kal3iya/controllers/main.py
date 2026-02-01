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
            qty = item.get('quantity')
            dum = item.get('dum')     # Optional
            garage = item.get('garage') # Optional
            
            # Call Model Validation
            res = Stock.validate_stock_exit({
                'product_name': product_name,
                'lot': lot,
                'qty': qty,
                'dum': dum,
                'garage': garage
            })
            
            if not res['valid']:
                # Using the first error message if multiple
                error_msg = res['errors'][0] if res['errors'] else "Unknown error"
                
                err_obj = {
                    'product': product_name,
                    'lot': lot,
                    'error': error_msg
                }
                # Add available qty if present (e.g. insufficient stock error)
                if res.get('available_qty') is not None:
                     err_obj['available_qty'] = res['available_qty']
                
                errors.append(err_obj)

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
