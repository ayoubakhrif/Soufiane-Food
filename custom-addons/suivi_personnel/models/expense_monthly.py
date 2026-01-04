from odoo import models, fields, api

class ExpenseMonthly(models.Model):
    _name = 'suivi.expense.monthly'
    _description = 'Dépense Mensuelle'
    _order = 'category_id'

    category_id = fields.Many2one(
        'suivi.expense.category',
        string='Catégorie',
        required=True,
        ondelete='restrict'
    )
    amount = fields.Float(string='Montant', required=True)
    description = fields.Text(string='Description')
    
    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True
    )

    @api.depends('category_id')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.category_id.name if rec.category_id else 'Dépense'
