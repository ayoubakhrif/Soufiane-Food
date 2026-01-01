from odoo import models, fields

class CasaProduct(models.Model):
    _name = 'casa.product'
    _description = 'Produits Casa'

    name = fields.Char(string='Nom', required=True)
    image_1920 = fields.Image(string='Image')
