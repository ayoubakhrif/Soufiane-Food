import os

filepath = 'custom-addons/tanger_med/models/finance2_cheque_inherit.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_fields = """    sutra_facture_ids = fields.One2many('sutra.facture', 'cheque_id', string='Factures SUTRA liees')
    is_sutra_benif = fields.Boolean(compute='_compute_is_sutra_benif')

    @api.depends('benif_id', 'benif_id.name')
    def _compute_is_sutra_benif(self):
        for rec in self:
            rec.is_sutra_benif = bool(rec.benif_id and rec.benif_id.name and 'sutra' in rec.benif_id.name.lower())
"""

content = content.replace("    sutra_facture_ids = fields.One2many('sutra.facture', 'cheque_id', string='Factures SUTRA liees')", new_fields)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated python model")
