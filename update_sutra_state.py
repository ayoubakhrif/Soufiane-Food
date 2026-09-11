import os

filepath_py = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath_py, 'r', encoding='utf-8') as f:
    content = f.read()

# Modify payment_state
old_state = """    payment_state = fields.Selection([
        ('non_paye', 'Non Paye'),
        ('paye', 'Paye')
    ], string='Etat de Paiement', compute='_compute_payment_state', store=True)"""
new_state = """    payment_state = fields.Selection([
        ('sans_facture', 'Pas de facture'),
        ('non_paye', 'Non Paye'),
        ('paye', 'Paye')
    ], string='Etat de Paiement', compute='_compute_payment_state', store=True)"""
content = content.replace(old_state, new_state)

old_compute_state = """    @api.depends('facture_ids', 'facture_ids.state')
    def _compute_payment_state(self):
        for rec in self:
            if not rec.facture_ids:
                rec.payment_state = 'non_paye'
            elif all(f.state == 'paye' for f in rec.facture_ids):
                rec.payment_state = 'paye'
            else:
                rec.payment_state = 'non_paye'"""
new_compute_state = """    @api.depends('facture_ids', 'facture_ids.state')
    def _compute_payment_state(self):
        for rec in self:
            if not rec.facture_ids:
                rec.payment_state = 'sans_facture'
            elif all(f.state == 'paye' for f in rec.facture_ids):
                rec.payment_state = 'paye'
            else:
                rec.payment_state = 'non_paye'"""
content = content.replace(old_compute_state, new_compute_state)

with open(filepath_py, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra.py payment_state")
