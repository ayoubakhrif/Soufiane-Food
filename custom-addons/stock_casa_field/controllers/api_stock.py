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

class CasaStockApiController(http.Controller):

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



    @http.route('/api/casa/login', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_login(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        phone = (data.get('phone') or '').strip()
        password = (data.get('password') or '').strip()

        if not phone or not password:
            return self._json_response({'status': 'error', 'message': 'Veuillez saisir le numero de telephone et le mot de passe.'}, status=400)

        agent = request.env['casa_field.stock.agent'].sudo().search([('phone', '=', phone), ('active', '=', True)], limit=1)
        if agent and agent.password == password:
            return self._json_response({'status': 'success', 'agent': {'id': agent.id, 'name': agent.name, 'phone': agent.phone, 'role': agent.role}})

        driver = request.env['casa_field.stock.driver'].sudo().search([('phone', '=', phone)], limit=1)
        if driver and driver.password == password:
            return self._json_response({'status': 'success', 'agent': {'id': driver.id, 'name': driver.name, 'phone': driver.phone, 'role': 'driver'}})

        return self._json_response({'status': 'error', 'message': 'Numero de telephone ou mot de passe incorrect.'}, status=401)

    @http.route('/api/casa/bootstrap', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_bootstrap(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        products = request.env['casa_field.stock.product'].sudo().search_read(
            [], ['id', 'name']
        )
        clients = request.env['casa_field.stock.client'].sudo().search_read(
            [], ['id', 'name']
        )
        drivers = request.env['casa_field.stock.driver'].sudo().search_read(
            [], ['id', 'name']
        )

        return self._json_response({
            'status': 'success',
            'products': products,
            'clients': clients,
            'drivers': drivers,
            'garages': GARAGE_SELECTION,
        })

    @http.route('/api/casa/stock', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_stock(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        stock_records = request.env['casa_field.stock.stock'].sudo().search([('quantity', '>', 0)])
        data = []
        for rec in stock_records:
            # Chercher d'abord la photo d'emballage prise lors de l'entreƒÂ©e du lot
            image_b64 = ''
            entry = request.env['casa_field.stock.entry'].sudo().search([
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
                'frigo': rec.frigo or 'stock_casa',
                'image': image_b64,
            })

        return self._json_response({
            'status': 'success',
            'count': len(data),
            'stock': data,
        })

    @http.route('/api/casa/entry', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_entry(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            vals = {
                'product_id': int(data.get('product_id')),
                'frigo': data.get('frigo') or 'stock_casa',
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

            entry = request.env['casa_field.stock.entry'].sudo().create(vals)
            entry.action_confirm()

            return self._json_response({
                'status': 'success',
                'entry_id': entry.id,
                'name': entry.name,
                'message': f"EntreƒÂ©e {entry.name} enregistreƒÂ©e avec succeƒÂ¨s."
            })
        except Exception as e:
            _logger.exception("Erreur API Entry")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route('/api/casa/exit', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_exit(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            vals = {
                'product_id': int(data.get('product_id')),
                'client_id': int(data.get('client_id')) if data.get('client_id') else False,
                'frigo': data.get('frigo') or 'stock_casa',
                'lot': data.get('lot') or '',
                'dum': data.get('dum') or '',
                'calibre': data.get('calibre') or '',
                'weight': float(data.get('weight', 0)),
                'qty': float(data.get('qty', 0)),
                'date': self._sanitize_date(data.get('date')),
            }

            exit_rec = request.env['casa_field.stock.exit'].sudo().create(vals)
            exit_rec.action_register()

            return self._json_response({
                'status': 'success',
                'exit_id': exit_rec.id,
                'name': exit_rec.name,
                'message': f"Sortie {exit_rec.name} enregistreƒÂ©e avec succeƒÂ¨s."
            })
        except Exception as e:
            _logger.exception("Erreur API Exit")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)


    @http.route('/api/casa/bulk_exit', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
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
                product_id = int(line.get('product_id'))
                lot = line.get('lot') or ''
                dum = line.get('dum') or ''
                frigo = line.get('frigo') or 'stock_casa'
                
                # Fetch original weight and calibre from the entry in stock.move
                move = request.env['casa_field.stock.move'].sudo().search([
                    ('product_id', '=', product_id),
                    ('lot', '=', lot),
                    ('dum', '=', dum),
                    ('frigo', '=', frigo),
                    ('state', '=', 'done')
                ], limit=1)
                
                vals = {
                    'product_id': product_id,
                    'client_id': int(line.get('client_id')) if line.get('client_id') else False,
                    'frigo': frigo,
                    'lot': lot,
                    'dum': dum,
                    'qty': float(line.get('qty', 0)),
                    'date': self._sanitize_date(line.get('date')),
                    'driver_id': driver_id,
                    'order_reference': order_ref,
                    'weight': move.weight if move else 0.0,
                    'calibre': move.calibre if move else '',
                }
                exit_rec = request.env['casa_field.stock.exit'].sudo().create(vals)
                exit_rec.action_register()
                created_exits.append(exit_rec.id)


            try:
                driver_name = request.env['casa_field.stock.driver'].sudo().browse(driver_id).name if driver_id else "Inconnu"
                msg = f"ðŸšš *Nouvelle Tournee Validee (Casa)*\n"
                exits_records = request.env['casa_field.stock.exit'].sudo().browse(created_exits)
                refs = ", ".join(exits_records.mapped('name'))
                msg += f"Ref: {refs}\n"
                msg += f"Chauffeur: {driver_name}\n"
                msg += f"Nombre de sorties: {len(lines)}\n\n"
                
                for line in lines:
                    product = request.env['casa_field.stock.product'].sudo().browse(int(line.get('product_id'))).name
                    client_id = line.get('client_id')
                    client = request.env['casa_field.stock.client'].sudo().browse(int(client_id)).name if client_id else "Inconnu"
                    qty = line.get('qty', 0)
                    msg += f"- {product} ({qty} u) -> {client}\n"
                
                payload = {
                    "group_id": "120363049891261462@g.us",
                    "text": msg
                }
                import requests
                requests.post("http://172.17.0.1:3000/api/send", json=payload, timeout=5)
            except Exception as e:
                _logger.error(f"WhatsApp send error: {str(e)}")

            return self._json_response({'status': 'success', 'message': f'{len(created_exits)} sorties crees avec succes.'})
        except Exception as e:
            _logger.exception("Erreur API Bulk Exit")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)

    @http.route('/api/casa/exits', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_exits(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        domain = [('state', 'in', ['done', 'registered'])]
        exits = request.env['casa_field.stock.exit'].sudo().search(domain, order='date desc, id desc', limit=100)
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
                    'qty': rec.qty,
                    'returned_qty': returned_qty,
                    'state': rec.state,
                })

        return self._json_response({
            'status': 'success',
            'exits': data,
        })


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
            
        domain = [('state', 'in', ['done', 'delivered', 'registered'])]
        exits = request.env['casa_field.stock.exit'].sudo().search(domain, order='date desc, id desc', limit=200)
        
        data = []
        base_url = 'https://gestia-soufianefoods.cloud'
        
        for rec in exits:
            image_url = ""
            if rec.lot and rec.product_id:
                entry = request.env['casa_field.stock.entry'].sudo().search([
                    ('product_id', '=', rec.product_id.id),
                    ('lot', '=', rec.lot)
                ], limit=1)
                if entry and entry.photo_packaging:
                    image_url = f"{base_url}/api/casa/image/casa_field.stock.entry/{entry.id}/photo_packaging"
                
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



    @http.route('/api/casa/image/<string:model>/<int:id>/<string:field>', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_image(self, model, id, field, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
            
        try:
            record = request.env[model].sudo().browse(id)
            if not record.exists():
                return request.not_found()
                
            image_base64 = getattr(record, field)
            if not image_base64:
                return request.not_found()
                
            import base64
            image_data = base64.b64decode(image_base64)
            headers = [('Content-Type', 'image/jpeg')]
            return request.make_response(image_data, headers=headers)
        except Exception as e:
            return request.not_found()



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

    @http.route('/api/casa/return', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')

    def api_return(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_id = int(data.get('exit_id'))
            exit_rec = request.env['casa_field.stock.exit'].sudo().browse(exit_id)
            if not exit_rec.exists():
                return self._json_response({'status': 'error', 'message': 'Sortie introuvable.'}, status=404)

            vals = {
                'exit_id': exit_id,
                'qty': float(data.get('qty', 0)),
                'weight': exit_rec.weight,
                'date': self._sanitize_date(data.get('date')),
            }

            ret_rec = request.env['casa_field.stock.return'].sudo().create(vals)
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

    @http.route('/api/casa/driver_exits', type='http', auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False, cors='*')
    def api_driver_exits(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        driver_id = data.get('driver_id')
        if not driver_id:
            return self._json_response({'status': 'error', 'message': 'Chauffeur non specifie'}, status=400)
            
        domain = [('driver_id', '=', int(driver_id)), ('state', 'in', ['done', 'delivered'])]
        exits = request.env['casa_field.stock.exit'].sudo().search(domain, order='date desc, id desc')
        
        result = []
        for rec in exits:
            image_b64 = ''
            if rec.product_id:
                entry = request.env['casa_field.stock.entry'].sudo().search([
                    ('product_id', '=', rec.product_id.id),
                    ('lot', '=', rec.lot),
                    ('photo_packaging', '!=', False)
                ], limit=1, order='date desc, id desc')

                if entry and entry.photo_packaging:
                    image_b64 = entry.photo_packaging.decode('utf-8') if isinstance(entry.photo_packaging, bytes) else str(entry.photo_packaging)
                elif rec.product_id.image_1920:
                    img = rec.product_id.image_1920
                    image_b64 = img.decode('utf-8') if isinstance(img, bytes) else str(img)

            result.append({
                'id': rec.id,
                'name': rec.name,
                'date': str(rec.date),
                'product_name': rec.product_id.name if rec.product_id else '',
                'lot': rec.lot or '',
                'dum': rec.dum or '',
                'qty': rec.qty,
                'client_id': rec.client_id.id if rec.client_id else None,
                'client_name': rec.client_id.name if rec.client_id else '',
                'state': rec.state,
                'order_reference': rec.order_reference or '',
                'image_b64': image_b64,
            })
        return self._json_response({'status': 'success', 'exits': result})

    @http.route('/api/casa/mark_delivered', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_mark_delivered(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        try:
            exit_ids = data.get('exit_ids', [])
            if not exit_ids:
                return self._json_response({'status': 'error', 'message': 'Aucune sortie specifiee'}, status=400)
                
            exits = request.env['casa_field.stock.exit'].sudo().browse(exit_ids)
            exits.action_deliver()
            
            return self._json_response({'status': 'success', 'message': 'Mise a jour reussie'})
        except Exception as e:
            _logger.exception("Erreur API Mark Delivered")
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)
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
                return self._json_response({'status': 'error', 'message': 'Données invalides'}, status=400)
                
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
            return self._json_response({'status': 'success', 'message': 'Commande envoyée', 'order_id': order.id})

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
            return self._json_response({'status': 'success', 'message': 'Commande préparée'})
        return self._json_response({'status': 'error', 'message': 'Commande introuvable'}, status=404)
