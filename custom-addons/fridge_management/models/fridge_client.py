from odoo import models, fields

class FridgeClient(models.Model):
    _name = 'fridge.client'
    _description = 'Client (Locataire Frigo)'

    name = fields.Char(string="Nom de la société", required=True)
    phone = fields.Char(string="Téléphone")
    email = fields.Char(string="Email")
    deposit_ids = fields.One2many('fridge.deposit', 'client_id', string="Dossiers de Dépôt")
