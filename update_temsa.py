import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add amount_temsa to sutra.config.ste
content = content.replace("amount_multiple = fields.Float(string='Montant (Plusieurs)', required=True)", "amount_multiple = fields.Float(string='Montant (Plusieurs)', required=True)\n    amount_temsa = fields.Float(string='Montant TEMSA')")

# 2. Modify SutraDossier amount to be computed
old_amount = "amount = fields.Float(string='Montant SUTRA', tracking=True)"
new_amount = """amount = fields.Float(string='Montant SUTRA', compute='_compute_sutra_amount', store=True, readonly=False, tracking=True)

    @api.depends('logistics_id.container_count', 'logistics_id.passed_control_type', 'logistics_id.ste_id')
    def _compute_sutra_amount(self):
        for rec in self:
            if rec.logistics_id and rec.logistics_id.ste_id:
                config = self.env['sutra.config.ste'].search([('ste_id', '=', rec.logistics_id.ste_id.id)], limit=1)
                if config:
                    amt = config.amount_multiple if getattr(rec.logistics_id, 'container_count', 0) > 1 else config.amount_single
                    if getattr(rec.logistics_id, 'passed_control_type', 'none') in ('visite', 'analyse', 'both'):
                        amt += config.amount_temsa
                    rec.amount = amt"""

content = content.replace(old_amount, new_amount)

# Remove the static assignment from create()
old_create = """                    if not vals.get('amount') and log_entry.ste_id:
                        config = self.env['sutra.config.ste'].search([('ste_id', '=', log_entry.ste_id.id)], limit=1)
                        if config:
                            if log_entry.container_count and log_entry.container_count > 1:
                                vals['amount'] = config.amount_multiple
                            else:
                                vals['amount'] = config.amount_single"""
new_create = """                    # Amount is now handled by the compute method _compute_sutra_amount"""
content = content.replace(old_create, new_create)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra.py")
