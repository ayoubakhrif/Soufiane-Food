from odoo import models, fields

class StockKal3iyaSte(models.Model):
    _name = 'stock.kal3iya.ste'
    _description = 'Société Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)
    logo = fields.Binary(string="Logo")
    address = fields.Text(string='Adresse')



