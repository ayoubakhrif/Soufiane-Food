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

    is_onicl = fields.Boolean(
        string='Est ONICL',
        default=False,
        help="Cocher si cet article est assujetti à l'ONICL."
    )

    company_article_image = fields.Image(
        string='Image',
        related='company_article_id.image',
        readonly=True
    )

    alias_ids = fields.One2many(
        related='company_article_id.alias_ids',
        readonly=False,
        string='Traductions Darija'
    )
