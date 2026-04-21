from odoo import models, fields

class AchatArticle(models.Model):
    _inherit = 'achat.article'

    alias_ids = fields.One2many('achat.article.alias', 'article_id', string='Traductions Darija')

class AchatArticleAlias(models.Model):
    _name = 'achat.article.alias'
    _description = 'Alias Darija pour Article Achat'

    article_id = fields.Many2one('achat.article', string='Article', ondelete='cascade')
    name = fields.Char(string='Alias (Darija)', required=True)
