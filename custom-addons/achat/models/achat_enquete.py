from odoo import models, fields, api

class AchatArticlePrice(models.Model):
    _name = 'achat.article.price'
    _description = 'Purchase Article Price History'
    _order = 'date desc'

    # Core fields
    article_id = fields.Many2one(
        'logistique.article',
        string='Article',
        required=True,
        index=True
    )

    supplier_id = fields.Many2one(
        'logistique.supplier',
        string='Supplier',
        required=True,
        index=True
    )

    price = fields.Float(
        string='Price',
        required=True,
        digits=(16, 4)
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True
    )

    # Optional but recommended
    remarks = fields.Char(
        string='Remarks',
        help='Conditions, MOQ, delivery delay, or any additional information'
    )

    user_id = fields.Many2one(
        'res.users',
        string='Entered By',
        default=lambda self: self.env.user,
        readonly=True
    )
