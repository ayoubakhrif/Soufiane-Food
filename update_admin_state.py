import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add admin_state field
old_state = """    state = fields.Selection(["""
new_state = """    admin_state = fields.Selection(related='state', readonly=False, tracking=False)
    state = fields.Selection(["""

content = content.replace(old_state, new_state)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque.py with admin_state field")
