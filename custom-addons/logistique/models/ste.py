from odoo import models, fields

class LogistiqueSte(models.Model):
    _name = 'logistique.ste'
    _description = 'Société'

    name = fields.Char(string='Nom', required=True)
