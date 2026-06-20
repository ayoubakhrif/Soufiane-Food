from odoo import models, fields

class SuiviClient(models.Model):
    _name = 'suivi.client'
    _description = 'Client Suivi Transport'

    name = fields.Char(string='Nom', required=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
        ('kenitra', 'Kenitra'),
        ('agadir', 'Agadir'),
        ('merakech', 'Merakech'),
        ('fes', 'Fes'),
        ('houssima', 'Houssima'),
    ], string='Ville')
