from odoo import models, fields

class CasaDriver(models.Model):
    _name = 'casa.driver'
    _description = 'Chauffeurs Casa'

    name = fields.Char(string='Nom', required=True)
