import os

filepath = 'custom-addons/finance_2/models/personne.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_method = """
    def get_divers_breakdown(self):
        self.ensure_one()
        breakdown = {}
        for chq in self.cheque_ids.filtered(lambda c: c.state != 'annule'):
            ste_name = chq.ste_id.name or 'Inconnue'
            if ste_name not in breakdown:
                breakdown[ste_name] = {'nb_t': 0, 'mt_t': 0.0, 'nb_e': 0, 'mt_e': 0.0, 'nb_ne': 0, 'mt_ne': 0.0}
            
            breakdown[ste_name]['nb_t'] += 1
            breakdown[ste_name]['mt_t'] += chq.amount_total
            
            if chq.state == 'encaisse' or chq.date_encaissement:
                breakdown[ste_name]['nb_e'] += 1
                breakdown[ste_name]['mt_e'] += (chq.montant_encaisse or chq.amount_total)
            else:
                breakdown[ste_name]['nb_ne'] += 1
                breakdown[ste_name]['mt_ne'] += chq.amount_total
                
        v1_benifs = self.env['finance.benif'].sudo().search([('name', '=', self.name)])
        if v1_benifs:
            for v1_benif in v1_benifs:
                for chq in v1_benif.physical_chq_ids:
                    ste_name = chq.ste_id.name or 'Inconnue'
                    if ste_name not in breakdown:
                        breakdown[ste_name] = {'nb_t': 0, 'mt_t': 0.0, 'nb_e': 0, 'mt_e': 0.0, 'nb_ne': 0, 'mt_ne': 0.0}
                    breakdown[ste_name]['nb_t'] += 1
                    breakdown[ste_name]['mt_t'] += chq.amount_total
                    if chq.date_encaissement:
                        breakdown[ste_name]['nb_e'] += 1
                        breakdown[ste_name]['mt_e'] += chq.amount_total
                    else:
                        breakdown[ste_name]['nb_ne'] += 1
                        breakdown[ste_name]['mt_ne'] += chq.amount_total
                        
                for effet in v1_benif.effet_ids:
                    ste_name = effet.ste_id.name or 'Inconnue'
                    if ste_name not in breakdown:
                        breakdown[ste_name] = {'nb_t': 0, 'mt_t': 0.0, 'nb_e': 0, 'mt_e': 0.0, 'nb_ne': 0, 'mt_ne': 0.0}
                    breakdown[ste_name]['nb_t'] += 1
                    breakdown[ste_name]['mt_t'] += effet.montant
                    if effet.date_encaissement:
                        breakdown[ste_name]['nb_e'] += 1
                        breakdown[ste_name]['mt_e'] += effet.montant
                    else:
                        breakdown[ste_name]['nb_ne'] += 1
                        breakdown[ste_name]['mt_ne'] += effet.montant

        res = []
        for ste, vals in breakdown.items():
            vals['ste'] = ste
            res.append(vals)
        return res
"""

if "def get_divers_breakdown" not in content:
    content += new_method

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated personne.py")
