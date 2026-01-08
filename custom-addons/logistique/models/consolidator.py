from odoo import models, fields

class LogistiqueConsolidator(models.Model):
    _name = 'logistique.consolidater'
    _description = 'Consolidators'

    name = fields.Char(string='Nom', required=True)
