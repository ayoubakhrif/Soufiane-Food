import os
import re

talon_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2\models\talon.py'

with open(talon_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace etat field
old_etat = """    etat = fields.Selection([
        ('coffre', 'En Coffre'),
        ('actif', 'Actif'),
        ('cloture', 'Clôturé'),
    ], string='État', default='coffre', tracking=True)"""

new_etat = """    etat = fields.Selection([
        ('coffre', 'En Coffre'),
        ('actif', 'Actif'),
        ('cloture', 'Clôturé'),
    ], string='État', default='coffre', compute='_compute_etat', store=True, readonly=False, tracking=True)"""

content = content.replace(old_etat, new_etat)

# Replace constrains with depends
old_constrains = """    @api.constrains('cheque_ids')
    def _auto_update_etat(self):
        for rec in self:
            if rec.used_chqs == 0:
                rec.etat = 'coffre'
            elif rec.used_chqs > 0 and rec.used_chqs < rec.num_chq:
                rec.etat = 'actif'
            elif rec.used_chqs >= rec.num_chq:
                rec.etat = 'cloture'"""

new_depends = """    @api.depends('used_chqs', 'num_chq')
    def _compute_etat(self):
        for rec in self:
            if rec.used_chqs == 0:
                rec.etat = 'coffre'
            elif rec.used_chqs > 0 and rec.used_chqs < rec.num_chq:
                rec.etat = 'actif'
            elif rec.used_chqs >= rec.num_chq:
                rec.etat = 'cloture'"""

content = content.replace(old_constrains, new_depends)

with open(talon_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated talon.py")
