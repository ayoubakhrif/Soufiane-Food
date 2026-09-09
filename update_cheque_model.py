import os

filepath = 'custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add difference field
old_fields = "    montant_encaisse = fields.Float(string=\"Montant encaiss\\u00e9\", tracking=True)"
if "montant_encaisse = fields.Float" not in old_fields:
    # Just to be safe, find it
    pass

new_fields = """    montant_encaisse = fields.Float(string="Montant encaissé", tracking=True)
    difference = fields.Float(string="Différence", compute="_compute_difference", store=True)

    @api.depends('amount_total', 'montant_encaisse')
    def _compute_difference(self):
        for rec in self:
            if rec.state == 'encaisse' or rec.montant_encaisse:
                rec.difference = rec.amount_total - rec.montant_encaisse
            else:
                rec.difference = 0.0
"""
content = content.replace("    montant_encaisse = fields.Float(string=\"Montant encaiss\xc3\xa9\", tracking=True)", new_fields)

# Remove the warning in action_annuler_encaissement (that was accidentally there)
old_method = """    def action_annuler_encaissement(self):
        for rec in self:
            if rec.state == 'encaisse':
                rec.state = 'cloture'
                rec.date_encaissement = False
                rec.montant_encaisse = 0.0
            
            if rec.montant_encaisse != rec.amount_total:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Attention',
                        'message': 'Le montant encaiss\xc3\xa9 est diff\xc3\xa9rent du montant total du ch\xc3\xa8que.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }"""

new_method = """    def action_annuler_encaissement(self):
        for rec in self:
            if rec.state == 'encaisse':
                rec.state = 'cloture'
                rec.date_encaissement = False
                rec.montant_encaisse = 0.0"""
content = content.replace(old_method, new_method)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated python model")
