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

    @http.route('/api/kal3iya/login', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_login(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        phone = (data.get('phone') or '').strip()
        password = (data.get('password') or '').strip()

        if not phone or not password:
            return self._json_response({'status': 'error', 'message': 'Veuillez saisir le numéro de téléphone et le mot de passe.'}, status=400)

        agent = request.env['kal3iya.stock.agent'].sudo().search([('phone', '=', phone), ('active', '=', True)], limit=1)
        if agent and agent.password == password:
            return self._json_response({'status': 'success', 'agent': {'id': agent.id, 'name': agent.name, 'phone': agent.phone, 'role': 'agent'}})
            
        driver = request.env['kal3iya.stock.driver'].sudo().search([('phone', '=', phone)], limit=1)
        if driver and driver.password == password:
            return self._json_response({'status': 'success', 'agent': {'id': driver.id, 'name': driver.name, 'phone': driver.phone, 'role': 'driver'}})

        return self._json_response({'status': 'error', 'message': 'Numero de telephone ou mot de passe incorrect.'}, status=401)
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
            # Chercher d'abord la photo d'emballage prise lors de l'entrée du lot
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
                'ste_id': rec.ste_id.id if rec.ste_id else None,
                'ste_name': rec.ste_id.name if rec.ste_id else '',
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
                'agent_id': int(data.get('agent_id')) if data.get('agent_id') else False,
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
                'message': f"Entrée {entry.name} enregistrée avec succès."
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
                'agent_id': int(data.get('agent_id')) if data.get('agent_id') else False,
                'ste_id': int(data.get('ste_id')) if data.get('ste_id') else False,
            }

            exit_rec = request.env['kal3iya.stock.exit'].sudo().create(vals)
            exit_rec.action_confirm()

            return self._json_response({
                'status': 'success',
                'exit_id': exit_rec.id,
                'name': exit_rec.name,
                'message': f"Sortie {exit_rec.name} enregistrée avec succès."
            })
        except Exception as e:
            _logger.exception("Erreur API Exit")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route('/api/kal3iya/transfer', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_transfer(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            vals = {
                'product_id': int(data.get('product_id')),
                'garage_source': data.get('garage_source'),
                'garage_dest': data.get('garage_dest'),
                'frigo_source': data.get('frigo_source') or 'stock_kal3iya',
                'frigo_dest': data.get('frigo_dest') or 'stock_kal3iya',
                'lot': data.get('lot') or '',
                'dum': data.get('dum') or '',
                'calibre': data.get('calibre') or '',
                'weight': float(data.get('weight', 0)),
                'qty': float(data.get('qty', 0)),
                'date': self._sanitize_date(data.get('date')),
                'agent_id': int(data.get('agent_id')) if data.get('agent_id') else False,
                'ste_id': int(data.get('ste_id')) if data.get('ste_id') else False,
            }

            transfer = request.env['kal3iya.stock.transfer'].sudo().create(vals)
            transfer.action_confirm()

            return self._json_response({
                'status': 'success',
                'transfer_id': transfer.id,
                'name': transfer.name,
                'message': f"Transfert {transfer.name} enregistré avec succès."
            })
        except Exception as e:
            _logger.exception("Erreur API Transfer")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)
    @http.route('/api/kal3iya/exits', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')

    @http.route('/api/kal3iya/exits', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_exits(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        domain = [('state', '=', 'done')]
        exits = request.env['kal3iya.stock.exit'].sudo().search(domain, order='date desc, id desc', limit=100)
        data = []
        for rec in exits:
            returned_qty = sum(r.qty for r in rec.return_ids if r.state == 'done')
            if returned_qty < rec.qty: # Only send exits that can still be returned
                data.append({
                    'id': rec.id,
                    'name': rec.name,
                    'date': str(rec.date),
                    'product_name': rec.product_id.name if rec.product_id else '',
                    'lot': rec.lot or '',
                    'client_name': rec.client_id.name if rec.client_id else '',
                    'garage': rec.garage or '',
                    'qty': rec.qty,
                    'returned_qty': returned_qty,
                })

        return self._json_response({
            'status': 'success',
            'exits': data,
        })

    @http.route('/api/kal3iya/return', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_return(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_id = int(data.get('exit_id'))
            exit_rec = request.env['kal3iya.stock.exit'].sudo().browse(exit_id)
            if not exit_rec.exists():
                return self._json_response({'status': 'error', 'message': 'Sortie introuvable.'}, status=404)

            vals = {
                'exit_id': exit_id,
                'garage': data.get('garage'),
                'qty': float(data.get('qty', 0)),
                'date': self._sanitize_date(data.get('date')),
            }

            ret_rec = request.env['kal3iya.stock.return'].sudo().create(vals)
            ret_rec.action_confirm()

            return self._json_response({
                'status': 'success',
                'return_id': ret_rec.id,
                'name': ret_rec.name,
                'message': f'Retour {ret_rec.name} enregistre avec succes.'
            })
        except Exception as e:
            _logger.exception('Erreur API Return')
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

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
