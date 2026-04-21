from odoo import models, fields

class LogistiqueArticle(models.Model):
    _name = 'logistique.article'
    _description = 'Article'

    name = fields.Char(string='Nom', required=True)

    company_article_id = fields.Many2one(
        'company.article',
        string='Article Société',
    )
