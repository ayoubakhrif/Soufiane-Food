from odoo import models, fields

class CompanyArticle(models.Model):
    _inherit = 'company.article'

    alias_ids = fields.One2many('casa_hanane.article.alias', 'article_id', string='Traductions Darija')

class CasaProduct(models.Model):
    _inherit = 'casa_hanane.product'

    alias_ids = fields.One2many(related='article_id.alias_ids', readonly=False, string='Traductions Darija')

class CasaArticleAlias(models.Model):

    _name = 'casa_hanane.article.alias'
    _description = 'Alias Darija pour Article'

    article_id = fields.Many2one('company.article', string='Article', ondelete='cascade')
    name = fields.Char(string='Alias (Darija)', required=True)
