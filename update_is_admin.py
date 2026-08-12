import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add is_admin field and compute method
old_state = """    state = fields.Selection(["""
new_state = """    is_admin = fields.Boolean(compute='_compute_is_admin')

    def _compute_is_admin(self):
        for rec in self:
            rec.is_admin = self.env.user.has_group('finance_2.group_finance2_admin')

    state = fields.Selection(["""

content = content.replace(old_state, new_state)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque.py with is_admin field")
