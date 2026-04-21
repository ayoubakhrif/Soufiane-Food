from odoo import models, fields

class SuiviClient(models.Model):
    _name = 'suivi.client'
    _description = 'Client Suivi Transport'

    name = fields.Char(string='Nom', required=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
        # Add more if needed, standardizing based on other modules
    ], string='Ville')
