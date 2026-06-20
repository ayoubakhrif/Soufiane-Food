from odoo import models, fields

class SuiviFournisseur(models.Model):
    _name = 'suivi.fournisseur'
    _description = 'Fournisseur Suivi Transport'

    name = fields.Char(string='Nom', required=True)
    phone = fields.Char(string='Téléphone')
