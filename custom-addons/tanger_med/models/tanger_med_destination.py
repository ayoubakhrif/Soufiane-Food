from odoo import models, fields

class TangerMedDestination(models.Model):
    _name = 'tanger.med.destination'
    _description = 'Destination Tanger Med'
    
    name = fields.Char(string='Nom', required=True)
