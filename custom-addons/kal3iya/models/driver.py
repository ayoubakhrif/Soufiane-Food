from odoo import models, fields

class Kal3iyadriver(models.Model):
    _name = 'kal3iya.driver'
    _description = 'Chauffeurs'

    name = fields.Char(string='Chauffeur', required=True)
    phone = fields.Char(string='Téléphone')
    advance_ids = fields.One2many('kal3iya.advance', 'driver_id', string='Avances')
    client_id = fields.One2many('kal3iya.client', 'driver_id', string='Client')
