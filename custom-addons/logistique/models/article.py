from odoo import models, fields

class LogistiqueArticle(models.Model):
    _name = 'logistique.article'
    _description = 'Article'

    name = fields.Char(string='Nom', required=True)
    traduction = fields.Char(string='Traduction')
    to_follow = fields.Boolean(string="À suivre", default=False, help="Sélectionnez ce produit pour qu'il soit inclus dans le rapport quotidien des prix.")


    company_article_id = fields.Many2one(
        'company.article',
        string='Article Société',
    )
    
    detail_ids = fields.One2many('logistique.article.detail', 'article_id', string='Détails')
    packaging_ids = fields.One2many('logistique.article.packaging', 'article_id', string='Packagings')


class LogistiqueArticleDetail(models.Model):
    _name = 'logistique.article.detail'
    _description = 'Détail de l\'article'

    name = fields.Char(string='Détail', required=True)
    article_id = fields.Many2one('logistique.article', string='Article', required=True, ondelete='cascade')


class LogistiqueArticlePackaging(models.Model):
    _name = 'logistique.article.packaging'
    _description = 'Packaging de l\'article'

    name = fields.Char(string='Packaging', required=True)
    article_id = fields.Many2one('logistique.article', string='Article', required=True, ondelete='cascade')


class LogistiqueContainerSize(models.Model):
    _name = 'logistique.container.size'
    _description = 'Taille de Conteneur'

    name = fields.Char(string='Taille', required=True)

