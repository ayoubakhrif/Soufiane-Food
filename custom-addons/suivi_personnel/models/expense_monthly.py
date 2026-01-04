from odoo import models, fields, api

class ExpenseMonthly(models.Model):
    _name = 'suivi.expense.monthly'
    _description = 'Dépense Mensuelle'
    _order = 'category_id'

    category = fields.Char(
        string='Catégorie',
        required=True,
    )
    amount = fields.Float(string='Montant', required=True)
    description = fields.Text(string='Description')
    
    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True
    )

    @api.depends('category')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.category if rec.category else 'Dépense'
