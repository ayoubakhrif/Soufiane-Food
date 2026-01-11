from odoo import models, fields

class StockKal3iyaProduct(models.Model):
    _name = 'stock.kal3iya.product'
    _description = 'Produits Stock Kal3iya'

    company_article_id = fields.Many2one(
        'company.article',
        string='Article Société',
        required=True
    )

    name = fields.Char(
        string='Nom interne Kal3iya',
        required=True
    )

    company_article_image = fields.Image(
        string='Image',
        related='company_article_id.image',
        readonly=True
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le nom interne doit être unique.')
    ]


