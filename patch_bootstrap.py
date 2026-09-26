import codecs

with codecs.open('custom-addons/kal3iya_stock/controllers/api_stock.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        clients = request.env['kal3iya.stock.client'].sudo().search_read(
            [], ['id', 'name']
        )'''
new = '''        clients = request.env['kal3iya.stock.client'].sudo().search_read(
            [], ['id', 'name']
        )
        drivers = request.env['kal3iya.stock.driver'].sudo().search_read(
            [], ['id', 'name']
        )'''
content = content.replace(old, new)
content = content.replace("'clients': clients,", "'clients': clients,\n            'drivers': drivers,")

with codecs.open('custom-addons/kal3iya_stock/controllers/api_stock.py', 'w', encoding='utf-8') as f:
    f.write(content)
