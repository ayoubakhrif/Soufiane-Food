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
