# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SuiviCredit(models.Model):
    _name = 'suivi.credit'
    _description = 'Suivi des Crédits'
    _order = 'date desc, id desc'

    personne_id = fields.Many2one(
        'suivi.personne', 
        string='Personne', 
        required=True, 
        ondelete='cascade'
    )
    date = fields.Date(
        string='Date', 
        required=True, 
        default=fields.Date.context_today
    )
    amount = fields.Float(
        string='Montant Absolu', 
        required=True
    )
    signed_amount = fields.Float(
        string='Montant',
        compute='_compute_signed_amount',
        inverse='_inverse_signed_amount',
        store=True
    )
    
    @api.depends('amount', 'type')
    def _compute_signed_amount(self):
        for rec in self:
            if rec.type == 'credit':
                rec.signed_amount = -abs(rec.amount)
            else:
                rec.signed_amount = abs(rec.amount)

    def _inverse_signed_amount(self):
        for rec in self:
            rec.amount = abs(rec.signed_amount)
            if rec.signed_amount < 0:
                rec.type = 'credit'
            elif rec.signed_amount > 0:
                rec.type = 'debit'

    type = fields.Selection([
        ('credit', 'Crédit'),
        ('debit', 'Débit')
    ], string='Type', required=True, default='credit')
    
    state = fields.Selection([
        ('draft', 'Non Payé'),
        ('paid', 'Payé')
    ], string='État', default='draft')
    
    description = fields.Char(string='Détails')

    def action_pay(self):
        for rec in self:
            rec.write({'state': 'paid'})
