from odoo import models, fields

class TransportDestination(models.Model):
    _name = 'transport.destination'
    _description = 'Destination'
    _order = 'name'

    name = fields.Char(string='Nom de la destination', required=True)
    mandatory_return = fields.Boolean(string='Retour obligatoire', default=False)
