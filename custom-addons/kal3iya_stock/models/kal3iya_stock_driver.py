from odoo import models, fields

class Kal3iyaStockDriver(models.Model):
    _name = 'kal3iya.stock.driver'
    _description = 'Chauffeurs Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)
