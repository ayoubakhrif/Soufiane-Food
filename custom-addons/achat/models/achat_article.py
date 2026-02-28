from odoo import models, fields, api

class AchatArticle(models.Model):
    _name = 'achat.article'
    _description = 'Article Achat'

    company_article_id = fields.Many2one(
        'company.article',
        string='Article Société',
        required=True
    )

    name = fields.Char(
        string='Nom interne Achat',
        required=True
    )

    company_article_image = fields.Image(
        string='Image',
        related='company_article_id.image',
        readonly=True
    )
