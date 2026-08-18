from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TvaDecaissement(models.Model):
    _name = 'tva.decaissement'
    _description = 'Déclaration de décaissement'
    _rec_name = 'invoice_number'

    invoice_number = fields.Char(string='N° facture', required=True)
    designation = fields.Char(string='Désignation')
    amount_ht = fields.Float(string='Montant HT')
    tva_rate = fields.Float(string='Taux de TVA (%)')
    amount_tva = fields.Float(string='Montant de la TVA', compute='_compute_amounts', store=True)
    amount_ttc = fields.Float(string='Montant TTC', compute='_compute_amounts', store=True)
    
    fournisseur_id = fields.Many2one('tva.fournisseur', string='Nom ou raison sociale', required=True)
    fournisseur_if = fields.Char(related='fournisseur_id.if_number', string='IF de fournisseur', readonly=True)
    fournisseur_ice = fields.Char(related='fournisseur_id.ice_number', string='ICE de fournisseur', readonly=True)
    
    payment_method = fields.Selection([
        ('virement', 'Virement'),
        ('prelevement', 'Prélevement'),
        ('cheque', 'Chèque'),
        ('versement', 'Versement'),
        ('espece', 'Espèce')
    ], string='Mode de paiement')
    
    invoice_date = fields.Date(string='Date facture')
    payment_date = fields.Date(string='Date paiement')
    
    tva_code = fields.Char(string='Code TVA')
    prorata = fields.Float(string='Prorata (%)')

    @api.depends('amount_ht', 'tva_rate')
    def _compute_amounts(self):
        for record in self:
            record.amount_tva = record.amount_ht * (record.tva_rate / 100.0)
            record.amount_ttc = record.amount_ht + record.amount_tva

    @api.constrains('invoice_number', 'fournisseur_id')
    def _check_unique_invoice(self):
        for record in self:
            if record.invoice_number and record.fournisseur_id:
                domain = [
                    ('invoice_number', '=', record.invoice_number),
                    ('fournisseur_id', '=', record.fournisseur_id.id),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError("Une facture avec ce numéro et ce même fournisseur existe déjà.")

    @api.constrains('invoice_date', 'payment_date')
    def _check_payment_date(self):
        for record in self:
            if record.invoice_date and record.payment_date:
                diff = (record.payment_date - record.invoice_date).days
                if diff >= 120:
                    raise ValidationError("La différence entre la date de paiement et la date de facture ne peut pas être supérieure ou égale à 120 jours.")
