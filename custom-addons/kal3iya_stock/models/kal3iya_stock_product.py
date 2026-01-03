from odoo import models, fields

class Kal3iyaStockProduct(models.Model):
    _name = 'kal3iya.stock.product'
    _description = 'Produits Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)
    image_1920 = fields.Image(string='Image')
