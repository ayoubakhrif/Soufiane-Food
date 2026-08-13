import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add _sql_constraints
old_inherit = """    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='N° Chèque', required=False, tracking=True)"""

new_inherit = """    _inherit = ['mail.thread', 'mail.activity.mixin']

    _sql_constraints = [
        ('unique_cheque_ste', 'unique(name, ste_id)', 'Erreur : Ce numéro de chèque existe déjà pour cette société !')
    ]

    name = fields.Char(string='N° Chèque', required=False, tracking=True)"""

content = content.replace(old_inherit, new_inherit)

# 2. Update action_confirmer
old_confirmer = """    def action_confirmer(self):
        for rec in self:
            rec.state = 'reserve'"""

new_confirmer = """    def action_confirmer(self):
        for rec in self:
            missing_fields = []
            if not rec.journal:
                missing_fields.append("Journal")
            if not rec.name:
                missing_fields.append("N° Chèque")
            if not rec.amount_total:
                missing_fields.append("Montant Total")
            if not rec.date_emission:
                missing_fields.append("Date d'émission")
            if not rec.date_echeance:
                missing_fields.append("Date d'échéance")
            if not rec.ste_id:
                missing_fields.append("Société")
                
            if missing_fields:
                raise UserError("Vous ne pouvez pas confirmer ce chèque car les informations suivantes sont manquantes : " + ", ".join(missing_fields))
                
            rec.state = 'reserve'"""

content = content.replace(old_confirmer, new_confirmer)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated cheque.py constraints and action_confirmer.")
