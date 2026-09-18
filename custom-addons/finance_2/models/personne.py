from odoo import models, fields, api

class Finance2Personne(models.Model):
    _name = 'finance2.personne'
    _description = 'Personne (Logistique)'

    name = fields.Char(string='Nom complet', required=True)
    active = fields.Boolean(default=True)
    cheque_ids = fields.One2many('finance2.cheque', 'benif_id', string='Chèques')

class Finance2Ste(models.Model):
    _name = 'finance2.ste'
    _description = 'Société'

    name = fields.Char(string='Nom de la société', required=True)
    raison_social = fields.Char(string='Raison Sociale')
    active = fields.Boolean(default=True)
    cheque_ids = fields.One2many('finance2.cheque', 'benif_id', string='Chèques')

class Finance2Benif(models.Model):
    _name = 'finance2.benif'
    _description = 'Bénéficiaire'

    is_divers = fields.Boolean(string='Divers', default=False)
    is_sutra = fields.Boolean(string='SUTRA', default=False)
    name = fields.Char(string='Nom du bénéficiaire', required=True)
    active = fields.Boolean(default=True)
    cheque_ids = fields.One2many('finance2.cheque', 'benif_id', string='Chèques')

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
