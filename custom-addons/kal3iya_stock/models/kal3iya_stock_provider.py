from odoo import models, fields

class Kal3iyaStockProvider(models.Model):
    _name = 'kal3iya.stock.provider'
    _description = 'Fournisseurs Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)
