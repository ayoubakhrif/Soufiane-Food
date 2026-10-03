from odoo import models, fields

class CasaStockProduct(models.Model):
    _name = 'casa_field.stock.product'
    _description = 'Produits Stock Casa'

    company_article_id = fields.Many2one(
        'company.article',
        string='Article Société',
        required=True
    )

    name = fields.Char(
        string='Nom interne Casa',
        required=True
    )

    company_article_image = fields.Image(
        string='Image',
        related='company_article_id.image',
        readonly=True
    )
    
    image_emballage = fields.Image(
        string='Image Emballage',
        max_width=512,
        max_height=512
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le nom interne doit être unique.')
    ]