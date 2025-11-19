from odoo import models, fields

class Cal3iyadriver(models.Model):
    _name = 'cal3iya.driver'
    _description = 'Chauffeurs'

    name = fields.Char(string='Chauffeur', required=True)
    phone = fields.Char(string='Téléphone')