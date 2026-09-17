from odoo import models, fields

class TransportVehicle(models.Model):
    _name = 'transport.vehicle'
    _description = 'Vehicule de Transport'

    name = fields.Char(string='Nom du véhicule', required=True)
    matricule = fields.Char(string='Matricule', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today)

    trip_ids = fields.One2many('transport.trip', 'vehicle_id', string='Historique des Voyages')
    trip_remorque_ids = fields.One2many('transport.trip.remorque', 'vehicle_id', string='Historique Remorque')
