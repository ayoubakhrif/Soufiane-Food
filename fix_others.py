import codecs
import os

files_to_fix = [
    ('custom-addons/kal3iya_stock/models/kal3iya_stock_stock_stock.py', 'kal3iya_stock_move', 'kal3iya.stock.move'),
    ('custom-addons/stock_kal3iya/models/stock_kal3iya_stock_stock.py', 'stock_kal3iya_move', 'stock.kal3iya.move')
]

for filepath, table_name, model_name in files_to_fix:
    if os.path.exists(filepath):
        with codecs.open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if 'def init(self):' in line:
                new_lines.append('        import odoo\n')
                new_lines.append(f'        if not odoo.tools.table_exists(self.env.cr, "{table_name}"):\n')
                new_lines.append(f'            self.env["{model_name}"]._auto_init()\n')
        
        with codecs.open(filepath, 'w', encoding='utf-8') as f:
            f.write(''.join(new_lines))
