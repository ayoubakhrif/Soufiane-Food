# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SuiviPersonne(models.Model):
    _name = 'suivi.personne'
    _description = 'Registre des Personnes'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='Email')
    note = fields.Text(string='Notes')
    
    credit_ids = fields.One2many(
        'suivi.credit', 
        'personne_id', 
        string='Crédits & Débits'
    )
    
    total_credit = fields.Float(
        string='Total Crédits', 
        compute='_compute_totals', 
        store=True
    )
    total_debit = fields.Float(
        string='Total Débits', 
        compute='_compute_totals', 
        store=True
    )
    balance = fields.Float(
        string='Solde', 
        compute='_compute_totals', 
        store=True,
        help="Total Crédit - Total Débit"
    )

    @api.depends('credit_ids.amount', 'credit_ids.type')
    def _compute_totals(self):
        for rec in self:
            credits = sum(line.amount for line in rec.credit_ids if line.type == 'credit')
            debits = sum(line.amount for line in rec.credit_ids if line.type == 'debit')
            rec.total_credit = credits
            rec.total_debit = debits
            rec.balance = credits - debits

    def action_view_credits(self):
        self.ensure_one()
        return {
            'name': f'Crédits & Débits de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'suivi.credit',
            'view_mode': 'tree,form,pivot,graph',
            'domain': [('personne_id', '=', self.id)],
            'context': {'default_personne_id': self.id},
        }
