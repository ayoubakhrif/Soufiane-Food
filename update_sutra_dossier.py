import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_fields = """    dum = fields.Char(string='DUM', compute='_compute_dum', store=True)
    payment_state = fields.Selection([
        ('non_paye', 'Non Paye'),
        ('paye', 'Paye')
    ], string='Etat de Paiement', compute='_compute_payment_state', store=True)

    @api.depends('logistics_id', 'logistics_id.dum', 'logistics_id.tanger_med_dum')
    def _compute_dum(self):
        for rec in self:
            rec.dum = rec.logistics_id.tanger_med_dum or rec.logistics_id.dum or ''

    @api.depends('facture_ids', 'facture_ids.state')
    def _compute_payment_state(self):
        for rec in self:
            if not rec.facture_ids:
                rec.payment_state = 'non_paye'
            elif all(f.state == 'paye' for f in rec.facture_ids):
                rec.payment_state = 'paye'
            else:
                rec.payment_state = 'non_paye'

    @api.model_create_multi"""

if "payment_state = fields.Selection" not in content:
    content = content.replace("    @api.model_create_multi", new_fields)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added dum and payment_state to SutraDossier")
