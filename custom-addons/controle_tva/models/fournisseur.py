from odoo import models, fields

class TvaFournisseur(models.Model):
    _name = 'tva.fournisseur'
    _description = 'Fournisseur TVA'

    name = fields.Char(string='Nom ou raison sociale', required=True)
    if_number = fields.Char(string='IF de fournisseur')
    ice_number = fields.Char(string='ICE de fournisseur')
