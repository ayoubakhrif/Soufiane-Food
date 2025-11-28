from odoo import models, fields

class Kal3iyaproduct(models.Model):
    _name = 'kal3iya.product'
    _description = 'Produits'

    name = fields.Char(string='Produits', required=True)