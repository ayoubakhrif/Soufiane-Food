from odoo import models, fields

class LogistiqueArticle(models.Model):
    _name = 'logistique.article'
    _description = 'Article'

    name = fields.Char(string='Nom', required=True)
