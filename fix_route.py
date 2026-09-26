import codecs

filepath = 'custom-addons/kal3iya_stock/controllers/api_stock.py'
with codecs.open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_bootstrap = '''    def api_bootstrap(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':'''

new_bootstrap = '''    @http.route('/api/kal3iya/bootstrap', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_bootstrap(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':'''

content = content.replace(old_bootstrap, new_bootstrap)

with codecs.open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
