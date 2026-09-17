from odoo import models, fields

class TransportVehicle(models.Model):
    _name = 'transport.vehicle'
    _description = 'Vehicule de Transport'

    name = fields.Char(string='Matricule', required=True)
