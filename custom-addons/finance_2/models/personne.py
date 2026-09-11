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

