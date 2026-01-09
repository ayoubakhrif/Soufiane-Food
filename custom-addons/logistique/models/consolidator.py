from odoo import models, fields

class LogistiqueConsolidator(models.Model):
    _name = 'logistique.consolidator'
    _description = 'Consolidators'

    name = fields.Char(string='Nom', required=True)
