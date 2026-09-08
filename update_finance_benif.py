import os

filepath = 'custom-addons/finance/models/finance_benif.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Add helper method
helper_method = """
    def get_finance2_cheques(self, encours_only=False):
        self.ensure_one()
        f2_benifs = self.env['finance2.benif'].search([('name', '=', self.name)])
        if not f2_benifs:
            return self.env['finance2.cheque']
        domain = [('benif_id', 'in', f2_benifs.ids)]
        if encours_only:
            domain.append(('date_encaissement', '=', False))
        return self.env['finance2.cheque'].search(domain)
"""
if "def get_finance2_cheques" not in content:
    content = content.replace("def _compute_chq_totals(self):", helper_method + "\n    def _compute_chq_totals(self):")

# _compute_chq_totals
compute_replacement = """    def _compute_chq_totals(self):
        for rec in self:
            c_credit = sum(rec.physical_chq_ids.mapped('credit'))
            e_credit = sum(rec.effet_ids.mapped('montant'))
            f2_chqs = rec.get_finance2_cheques()
            f2_credit = sum(f2_chqs.mapped('amount_total'))
            rec.total_credit = c_credit + e_credit + f2_credit
            
            c_debit = sum(rec.physical_chq_ids.mapped('debit'))
            e_debit = sum(e.montant for e in rec.effet_ids if e.date_encaissement)
            f2_debit = sum(c.amount_total for c in f2_chqs if c.date_encaissement)
            rec.total_debit = c_debit + e_debit + f2_debit
            
            rec.solde = rec.total_credit - rec.total_debit"""
content = re.sub(r"def _compute_chq_totals\(self\):.*?rec\.solde = rec\.total_credit - rec\.total_debit", compute_replacement, content, flags=re.DOTALL)


# get_financial_breakdown
# Add F2 logic to get_financial_breakdown
f2_breakdown = """        for chq in self.get_finance2_cheques():
            if encours_only and chq.date_encaissement:
                continue

            ste_name = chq.ste_id.name or 'Inconnue'
            if ste_name not in breakdown:
                breakdown[ste_name] = {
                    'encaisse': 0.0, 
                    'non_encaisse': 0.0,
                    'count_encaisse': 0,
                    'count_non_encaisse': 0
                }
            
            amt = chq.amount_total
            if chq.date_encaissement:
                breakdown[ste_name]['encaisse'] += amt
                breakdown[ste_name]['count_encaisse'] += 1
            else:
                breakdown[ste_name]['non_encaisse'] += amt
                breakdown[ste_name]['count_non_encaisse'] += 1

        for e in self.effet_ids:"""
content = content.replace("for e in self.effet_ids:", f2_breakdown)

# get_cheque_stats
f2_stats = """        total_chqs = len(chqs) + len(effets)
        encaisse_chqs = len(chqs.filtered(lambda c: c.date_encaissement)) + len(effets.filtered(lambda e: e.date_encaissement))
        
        f2_chqs = self.get_finance2_cheques(encours_only)
        total_chqs += len(f2_chqs)
        encaisse_chqs += len(f2_chqs.filtered(lambda c: c.date_encaissement))"""
content = re.sub(r"total_chqs = len\(chqs\) \+ len\(effets\)\s+encaisse_chqs = len\(chqs.filtered\(lambda c: c.date_encaissement\)\) \+ len\(effets.filtered\(lambda e: e.date_encaissement\)\)", f2_stats, content)

# get_detailed_cheques
f2_details = """        for e in self.effet_ids:
            if encours_only and e.date_encaissement:
                continue
            detailed_chqs.append({
                'name': e.serie or 'Inconnu',
                'ste': e.ste_id.name or 'Inconnue',
                'date_echeance': e.date_echeance,
                'amount': e.montant,
                'factures': '',
                'persons': '',
                'types': 'Effet',
                'status': 'EncaissǸ' if e.date_encaissement else 'En cours',
                'date_encaissement': e.date_encaissement
            })

        for c in self.get_finance2_cheques(encours_only):
            detailed_chqs.append({
                'name': c.name or 'Inconnu',
                'ste': c.ste_id.name or 'Inconnue',
                'date_echeance': c.date_echeance,
                'amount': c.amount_total,
                'factures': '',
                'persons': c.personne_id.name if c.personne_id else '',
                'types': 'Chque V2' if c.type == 'cheque' else 'Effet V2',
                'status': 'EncaissǸ' if c.date_encaissement else 'En cours',
                'date_encaissement': c.date_encaissement
            })

        detailed_chqs.sort(key=lambda x: x['date_echeance'] or fields.Date.today())"""
content = re.sub(r"for e in self.effet_ids:.*?detailed_chqs.sort\(key=lambda x: x\['date_echeance'\] or fields.Date.today\(\)\)", f2_details, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated finance_benif.py")
