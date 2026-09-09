import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_fields = """    amount_unbilled = fields.Float(string='Dettes Engagees (Non facturees)', compute='_compute_sutra_debts')
    amount_unpaid = fields.Float(string='Dettes Reelles (A Payer)', compute='_compute_sutra_debts')
    amount_total_debt = fields.Float(string='Dette Totale SUTRA', compute='_compute_sutra_debts')

    def _compute_sutra_debts(self):
        for rec in self:
            if not rec.ste_id:
                rec.amount_unbilled = 0.0
                rec.amount_unpaid = 0.0
                rec.amount_total_debt = 0.0
                continue
            
            dossiers = self.env['sutra.dossier'].search([('logistics_id.ste_id', '=', rec.ste_id.id)])
            unbilled_amount = sum(d.amount for d in dossiers if not d.facture_ids)
            
            unpaid_invoices = self.env['sutra.facture'].search([
                ('sutra_id', 'in', dossiers.ids),
                ('state', 'in', ['non_paye', 'encours'])
            ])
            unpaid_amount = sum(unpaid_invoices.mapped('amount'))
            
            rec.amount_unbilled = unbilled_amount
            rec.amount_unpaid = unpaid_amount
            rec.amount_total_debt = unbilled_amount + unpaid_amount

"""

if "amount_unbilled = fields.Float" not in content:
    content = content.replace("    _sql_constraints = [", new_fields + "    _sql_constraints = [")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added financial fields to SutraConfigSte")
