import os

filepath = 'custom-addons/finance_2/models/personne.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_code = """
    total_credit = fields.Float(string='Total Crédit', compute='_compute_totals')
    total_encaisse = fields.Float(string='Total Encaissé', compute='_compute_totals')
    solde = fields.Float(string='Solde à ce jour', compute='_compute_totals')

    @api.depends('cheque_ids', 'cheque_ids.amount_total', 'cheque_ids.montant_encaisse', 'cheque_ids.state')
    def _compute_totals(self):
        for rec in self:
            credit = sum(c.amount_total for c in rec.cheque_ids if c.state != 'annule')
            encaisse = sum(c.montant_encaisse or c.amount_total for c in rec.cheque_ids if c.state == 'encaisse')
            rec.total_credit = credit
            rec.total_encaisse = encaisse
            rec.solde = credit - encaisse
"""
content = content + new_code + "\n"

if "from odoo import models, fields, api" not in content:
    content = content.replace("from odoo import models, fields", "from odoo import models, fields, api")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated personne.py")
