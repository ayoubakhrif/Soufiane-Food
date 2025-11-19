from odoo import models, fields

class Kal3iyadriver(models.Model):
    _name = 'kal3iya.employees'
    _description = 'Employés'

    name = fields.Char(string='Nom', required=True)