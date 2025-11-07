from odoo import models, fields

class Kal3iyadriver(models.Model):
    _name = 'kal3iya.driver'
    _description = 'Chauffeurs'

    name = fields.Char(string='Chauffeur', required=True)
    phone = fields.Char(string='Téléphone')