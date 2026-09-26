import codecs

filepath = 'custom-addons/kal3iya_stock/controllers/api_stock.py'
with codecs.open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_vals = '''                    'frigo': line.get('frigo') or 'stock_kal3iya',
                    'lot': line.get('lot') or '',
                    'qty': float(line.get('qty', 0)),'''

new_vals = '''                    'frigo': line.get('frigo') or 'stock_kal3iya',
                    'lot': line.get('lot') or '',
                    'dum': line.get('dum') or '',
                    'qty': float(line.get('qty', 0)),'''

content = content.replace(old_vals, new_vals)

with codecs.open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
