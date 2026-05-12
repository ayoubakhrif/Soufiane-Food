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
        string='Montant', 
        required=True
    )
    type = fields.Selection([
        ('credit', 'Crédit'),
        ('debit', 'Débit')
    ], string='Type', required=True, default='credit')
    
    description = fields.Text(string='Détails')
