import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from odoo.exceptions import ValidationError, exceptions', 'from odoo.exceptions import ValidationError, UserError')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed import error")
