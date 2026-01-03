from odoo import models, fields

class Kal3iyaStockSte(models.Model):
    _name = 'kal3iya.stock.ste'
    _description = 'Société Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)
    logo = fields.Binary(string="Logo")
    address = fields.Text(string='Adresse')
