from odoo import models, fields

class Kal3iyaprovider(models.Model):
    _name = 'kal3iya.provider'
    _description = 'Fournisseurs'

    name = fields.Char(string='Fournisseur', required=True)