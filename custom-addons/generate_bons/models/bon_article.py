from odoo import models, fields, api

class BonArticle(models.Model):
    _name = 'bon.article'
    _description = 'Article pour les bons'

    company_article_id = fields.Many2one('company.article', string='Article (Company Data)', required=True)
    name = fields.Char(string='Désignation', related='company_article_id.display_name', store=True)
    pu = fields.Float(string='Prix Unitaire', required=True, default=0.0)
