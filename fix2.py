import codecs

filepath = 'custom-addons/stock_casa_field/models/casa_field_stock_stock_stock.py'
with codecs.open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if 'def init(self):' in line:
        new_lines.append('        import odoo\n')
        new_lines.append('        if not odoo.tools.table_exists(self.env.cr, "casa_field_stock_move"):\n')
        new_lines.append('            self.env["casa_field.stock.move"]._auto_init()\n')

with codecs.open(filepath, 'w', encoding='utf-8') as f:
    f.write(''.join(new_lines))
