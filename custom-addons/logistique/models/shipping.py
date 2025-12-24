from odoo import models, fields

class LogistiqueShipping(models.Model):
    _name = 'logistique.shipping'
    _description = 'Compagnie Maritime'

    name = fields.Char(string='Nom', required=True)
