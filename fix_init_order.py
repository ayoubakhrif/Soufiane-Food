import codecs
import re

filepath = 'custom-addons/stock_casa_field/models/casa_field_stock_stock_stock.py'
with codecs.open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = content.replace(
    'def init(self):\n        tools.drop_view_if_exists(self.env.cr, self._table)',
    'def init(self):\n        tools.drop_view_if_exists(self.env.cr, self._table)\n        if not odoo.tools.table_exists(self.env.cr, \"casa_field_stock_move\"):\n            self.env[\"casa_field.stock.move\"]._auto_init()'
)

# We need to import odoo at the top if it's not there
if 'import odoo' not in new_content:
    new_content = 'import odoo\n' + new_content

with codecs.open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
