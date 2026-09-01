from odoo import models, fields, api
from datetime import datetime

class Finance2Comparison(models.Model):
    _name = 'finance2.comparison'
    _description = 'Audit et Comparaison (Ancien vs V2)'
    _order = 'date_audit desc'

    name = fields.Char(string='Nom de l\'audit', required=True, default=lambda self: f"Audit du {fields.Date.context_today(self).strftime('%d/%m/%Y')}")
    date_audit = fields.Datetime(string='Date d\'exécution', default=fields.Datetime.now, readonly=True)
    line_ids = fields.One2many('finance2.comparison.line', 'comparison_id', string='Résultats')

    def action_run_comparison(self):
        self.ensure_one()
        # Vider les anciennes lignes pour ce run si on relance
        self.line_ids.unlink()

        # Récupérer les données
        physicals = self.env['finance.cheque.physical'].search([])
        cheques_v2 = self.env['finance2.cheque'].search([])

        # Dictionnaires pour accès rapide (Clé: (numéro, nom_société))
        v1_dict = {}
        for p in physicals:
            if not p.name: continue
            ste_name = p.ste_id.name.strip().upper() if p.ste_id and p.ste_id.name else "INCONNU"
            v1_dict[(p.name.strip(), ste_name)] = p

        v2_dict = {}
        for c in cheques_v2:
            if not c.name: continue
            ste_name = c.ste_id.name.strip().upper() if c.ste_id and c.ste_id.name else "INCONNU"
            v2_dict[(c.name.strip(), ste_name)] = c

        all_keys = set(v1_dict.keys()).union(set(v2_dict.keys()))
        
        lines_to_create = []
        for key in all_keys:
            num, ste = key
            p = v1_dict.get(key)
            c = v2_dict.get(key)

            if p and not c:
                # Seulement V1
                lines_to_create.append({
                    'comparison_id': self.id,
                    'cheque_number': p.name,
                    'ste_name': p.ste_id.name if p.ste_id else "Inconnu",
                    'status': 'only_v1',
                    'v1_amount': p.amount_total,
                    'v2_amount': 0.0,
                    'diff_details': "Manquant dans Finance V2",
                })
            elif c and not p:
                # Seulement V2
                lines_to_create.append({
                    'comparison_id': self.id,
                    'cheque_number': c.name,
                    'ste_name': c.ste_id.name if c.ste_id else "Inconnu",
                    'status': 'only_v2',
                    'v1_amount': 0.0,
                    'v2_amount': c.amount_total,
                    'diff_details': "Nouveau ou absent de l'ancien module",
                })
            elif c and p:
                # Sur les deux, on compare
                diffs = []
                # Montant
                if abs(p.amount_total - c.amount_total) > 0.01:
                    diffs.append(f"Montant (Ancien: {p.amount_total} | V2: {c.amount_total})")
                # Date Emission
                if p.date_emission != c.date_emission:
                    d1 = p.date_emission.strftime('%d/%m/%Y') if p.date_emission else 'N/A'
                    d2 = c.date_emission.strftime('%d/%m/%Y') if c.date_emission else 'N/A'
                    diffs.append(f"Émission ({d1} vs {d2})")
                # Date Echeance
                if p.date_echeance != c.date_echeance:
                    d1 = p.date_echeance.strftime('%d/%m/%Y') if p.date_echeance else 'N/A'
                    d2 = c.date_echeance.strftime('%d/%m/%Y') if c.date_echeance else 'N/A'
                    diffs.append(f"Échéance ({d1} vs {d2})")
                
                if diffs:
                    lines_to_create.append({
                        'comparison_id': self.id,
                        'cheque_number': c.name,
                        'ste_name': c.ste_id.name if c.ste_id else "Inconnu",
                        'status': 'diff',
                        'v1_amount': p.amount_total,
                        'v2_amount': c.amount_total,
                        'diff_details': " | ".join(diffs),
                    })
                else:
                    lines_to_create.append({
                        'comparison_id': self.id,
                        'cheque_number': c.name,
                        'ste_name': c.ste_id.name if c.ste_id else "Inconnu",
                        'status': 'ok',
                        'v1_amount': p.amount_total,
                        'v2_amount': c.amount_total,
                        'diff_details': "Identiques",
                    })

        if lines_to_create:
            self.env['finance2.comparison.line'].create(lines_to_create)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class Finance2ComparisonLine(models.Model):
    _name = 'finance2.comparison.line'
    _description = 'Ligne d\'audit Comparatif'

    comparison_id = fields.Many2one('finance2.comparison', string='Audit', ondelete='cascade')
    cheque_number = fields.Char(string='Numéro du chèque')
    ste_name = fields.Char(string='Société')
    
    status = fields.Selection([
        ('only_v1', 'Manquant dans V2'),
        ('only_v2', 'Nouveau dans V2'),
        ('diff', 'Différence détectée'),
        ('ok', 'Identique')
    ], string='Statut')
    
    v1_amount = fields.Float(string='Montant (Ancien)')
    v2_amount = fields.Float(string='Montant (V2)')
    diff_details = fields.Text(string='Détails')
