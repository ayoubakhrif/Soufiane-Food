from odoo import models, fields

class IncomeMonthly(models.Model):
    _name = 'suivi.income.monthly'
    _description = 'Revenu Mensuel'
    _order = 'name'

    name = fields.Char(string='Libellé', required=True)
    amount = fields.Float(string='Montant', required=True)
    category = fields.Char(string='Catégorie')
    description = fields.Text(string='Description')
