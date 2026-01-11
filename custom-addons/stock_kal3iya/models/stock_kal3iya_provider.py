from odoo import models, fields

class StockKal3iyaProvider(models.Model):
    _name = 'stock.kal3iya.provider'
    _description = 'Fournisseurs Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)



