import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove is_admin and admin_state
old_state = """    admin_state = fields.Selection(related='state', readonly=False, tracking=False)
    is_admin = fields.Boolean(compute='_compute_is_admin')

    def _compute_is_admin(self):
        for rec in self:
            rec.is_admin = self.env.user.has_group('finance_2.group_finance2_admin')

    state = fields.Selection(["""

new_state = """    state = fields.Selection(["""
content = content.replace(old_state, new_state)

# Add force actions
actions_code = """
    def force_brouillon(self):
        for rec in self:
            rec.state = 'brouillon'

    def force_reserve(self):
        for rec in self:
            rec.state = 'reserve'

    def force_actif(self):
        for rec in self:
            rec.state = 'actif'

    def force_cloture(self):
        for rec in self:
            rec.state = 'cloture'
"""
content += actions_code

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque.py with force actions")
