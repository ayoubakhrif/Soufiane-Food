from odoo import models, fields

class Kal3iyadriver(models.Model):
    _name = 'kal3iya.driver'
    _description = 'Chauffeurs'

    name = fields.Char(string='Chauffeur', required=True)
    phone = fields.Char(string='Téléphone')
    advance_ids = fields.One2many('kal3iya.advance', 'driver_id', string='Avances')
    total_avance = fields.float(string='Total_avances', compute='_compute_total_avance')
    
