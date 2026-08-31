from odoo import models, fields, api

class BonArticleWeight(models.Model):
    _name = 'bon.article.weight'
    _description = 'Poids disponible pour un article'
    _order = 'weight asc'

    article_id = fields.Many2one('bon.article', string='Article', required=True, ondelete='cascade')
    weight = fields.Float(string='Poids (kg)', required=True)

class BonArticle(models.Model):
    _name = 'bon.article'
    _description = 'Article pour les bons'

    company_article_id = fields.Many2one('company.article', string='Article (Company Data)', required=True)
    name = fields.Char(string='Désignation', related='company_article_id.display_name', store=True)
    pu = fields.Float(string='Prix Unitaire', required=True, default=0.0)
    
    weight_ids = fields.One2many('bon.article.weight', 'article_id', string='Poids Disponibles')

    def get_default_weight(self):
        self.ensure_one()
        if self.weight_ids:
            return self.weight_ids[0].weight
        return 1.0 # Fallback if no weight defined
