import codecs

with codecs.open('custom-addons/stock_casa_field/controllers/api_stock.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_bootstrap = '''        clients = request.env['kal3iya.stock.client'].sudo().search_read(
            [], ['id', 'name']
        )

        return self._json_response({
            'status': 'success',
            'products': products,
            'clients': clients,
            'garages': GARAGE_SELECTION,
        })'''

new_bootstrap = '''        clients = request.env['kal3iya.stock.client'].sudo().search_read(
            [], ['id', 'name']
        )
        drivers = request.env['kal3iya.stock.driver'].sudo().search_read(
            [], ['id', 'name']
        )

        return self._json_response({
            'status': 'success',
            'products': products,
            'clients': clients,
            'drivers': drivers,
            'garages': GARAGE_SELECTION,
        })'''

content = content.replace(old_bootstrap, new_bootstrap)

with codecs.open('custom-addons/stock_casa_field/controllers/api_stock.py', 'w', encoding='utf-8') as f:
    f.write(content)
