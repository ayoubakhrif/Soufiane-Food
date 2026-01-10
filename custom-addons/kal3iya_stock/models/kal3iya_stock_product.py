from odoo import models, fields

class Kal3iyaStockProduct(models.Model):
    _name = 'kal3iya.stock.product'
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