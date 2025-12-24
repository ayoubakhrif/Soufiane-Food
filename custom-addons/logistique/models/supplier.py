from odoo import models, fields

class LogistiqueSupplier(models.Model):
    _name = 'logistique.supplier'
    _description = 'Fournisseur'

    name = fields.Char(string='Nom', required=True)
