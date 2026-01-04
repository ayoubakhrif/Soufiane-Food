from odoo import models, fields

class ExpenseCategory(models.Model):
    _name = 'suivi.expense.category'
    _description = 'Catégorie de Dépense'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Actif', default=True)
