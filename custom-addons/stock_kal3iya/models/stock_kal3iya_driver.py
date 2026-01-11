from odoo import models, fields

class StockKal3iyaDriver(models.Model):
    _name = 'stock.kal3iya.driver'
    _description = 'Chauffeurs Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)



