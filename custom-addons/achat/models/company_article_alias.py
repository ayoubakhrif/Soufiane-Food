from odoo import models, fields

class CompanyArticle(models.Model):
    _inherit = 'company.article'

    alias_ids = fields.One2many('company.article.alias', 'article_id', string='Traductions Darija')

class CompanyArticleAlias(models.Model):
    _name = 'company.article.alias'
    _description = 'Alias Darija pour Article Société'

    article_id = fields.Many2one('company.article', string='Article Société', ondelete='cascade')
    name = fields.Char(string='Alias (Darija)', required=True)
