import json
import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

GARAGE_SELECTION = [
    {'key': 'garage1', 'label': 'Garage 1'},
    {'key': 'garage2', 'label': 'Garage 2'},
    {'key': 'garage3', 'label': 'Garage 3'},
    {'key': 'garage4', 'label': 'Garage 4'},
    {'key': 'garage5', 'label': 'Garage 5'},
    {'key': 'garage6', 'label': 'Garage 6'},
    {'key': 'garage7', 'label': 'Garage 7'},
    {'key': 'garage8', 'label': 'Garage 8'},
    {'key': 'terrasse', 'label': 'Terrasse'},
    {'key': 'fenidek', 'label': 'Fenidek'},
]

class Kal3iyaStockApiController(http.Controller):

    def _json_response(self, data, status=200):
        headers = [
            ('Content-Type', 'application/json'),
        ]
        return request.make_response(
            json.dumps(data, ensure_ascii=False, default=str),
            headers=headers,
            status=status
        )

    def _get_request_data(self):
        try:
            if request.httprequest.data:
                return json.loads(request.httprequest.data.decode('utf-8'))
        except Exception:
            pass
        return request.params or {}

    def _sanitize_date(self, date_val):
        if date_val and date_val != '--':
            try:
                date_str = str(date_val).strip()
                if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                    return date_str
            except Exception:
                pass
        return fields.Date.context_today(request.env.user)


    @http.route('/api/kal3iya/bootstrap', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_bootstrap(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        products = request.env['kal3iya.stock.product'].sudo().search_read(
            [], ['id', 'name']
        )
        clients = request.env['kal3iya.stock.client'].sudo().search_read(
            [], ['id', 'name']
        )

        return self._json_response({
            'status': 'success',
            'products': products,
            'clients': clients,
            'garages': GARAGE_SELECTION,
        })

    @http.route('/api/kal3iya/stock', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_stock(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        stock_records = request.env['kal3iya.stock.stock'].sudo().search([('quantity', '>', 0)])
        data = []
        for rec in stock_records:
            # Chercher d'abord la photo d'emballage prise lors de l'entrÃ©e du lot
            image_b64 = ''
            entry = request.env['kal3iya.stock.entry'].sudo().search([
                ('product_id', '=', rec.product_id.id),
                ('lot', '=', rec.lot),
                ('photo_packaging', '!=', False)
            ], limit=1, order='date desc, id desc')
            
            if entry and entry.photo_packaging:
                image_b64 = entry.photo_packaging.decode('utf-8') if isinstance(entry.photo_packaging, bytes) else str(entry.photo_packaging)
            elif rec.image_1920:
                image_b64 = rec.image_1920.decode('utf-8') if isinstance(rec.image_1920, bytes) else str(rec.image_1920)

            data.append({
                'id': rec.id,
                'product_id': rec.product_id.id if rec.product_id else None,
                'product_name': rec.product_id.name if rec.product_id else '',
                'lot': rec.lot or '',
                'dum': rec.dum or '',
                'calibre': rec.calibre or '',
                'weight': rec.weight or 0.0,
                'quantity': rec.quantity or 0.0,
                'garage': rec.garage or '',
                'frigo': rec.frigo or 'stock_kal3iya',
                'image': image_b64,
            })

        return self._json_response({
            'status': 'success',
            'count': len(data),
            'stock': data,
        })

    @http.route('/api/kal3iya/entry', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_entry(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            vals = {
                'product_id': int(data.get('product_id')),
                'garage': data.get('garage'),
                'frigo': data.get('frigo') or 'stock_kal3iya',
                'lot': data.get('lot'),
                'dum': data.get('dum'),
                'calibre': data.get('calibre') or '',
                'qty': float(data.get('qty', 0)),
                'weight': float(data.get('weight', 0)),
                'date': self._sanitize_date(data.get('date')),
            }
            if data.get('photo_packaging'):
                vals['photo_packaging'] = data.get('photo_packaging')
            if data.get('photo_container'):
                vals['photo_container'] = data.get('photo_container')

            entry = request.env['kal3iya.stock.entry'].sudo().create(vals)
            entry.action_confirm()

            return self._json_response({
                'status': 'success',
                'entry_id': entry.id,
                'name': entry.name,
                'message': f"EntrÃ©e {entry.name} enregistrÃ©e avec succÃ¨s."
            })
        except Exception as e:
            _logger.exception("Erreur API Entry")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route('/api/kal3iya/exit', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_exit(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            vals = {
                'product_id': int(data.get('product_id')),
                'client_id': int(data.get('client_id')) if data.get('client_id') else False,
                'garage': data.get('garage'),
                'frigo': data.get('frigo') or 'stock_kal3iya',
                'lot': data.get('lot') or '',
                'dum': data.get('dum') or '',
                'calibre': data.get('calibre') or '',
                'weight': float(data.get('weight', 0)),
                'qty': float(data.get('qty', 0)),
                'date': self._sanitize_date(data.get('date')),
            }

            exit_rec = request.env['kal3iya.stock.exit'].sudo().create(vals)
            exit_rec.action_confirm()

            return self._json_response({
                'status': 'success',
                'exit_id': exit_rec.id,
                'name': exit_rec.name,
                'message': f"Sortie {exit_rec.name} enregistrÃ©e avec succÃ¨s."
            })
        except Exception as e:
            _logger.exception("Erreur API Exit")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

