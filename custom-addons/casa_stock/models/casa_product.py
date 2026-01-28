from odoo import models, fields

class CasaProduct(models.Model):
    _name = 'casa.product'
    _description = 'Produits Casa'

    name = fields.Char(string='Nom', required=True)
    article_id = fields.Many2one('company.article', string='Article (Company)', required=True)
    image_1920 = fields.Image(related='article_id.image', string='Image', store=True, readonly=True)
