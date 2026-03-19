from odoo import models, fields

class TresorerieClient(models.Model):
    _name = 'tresorerie.client'
    _description = 'Client (Trésorerie)'

    name = fields.Char(string='Nom', required=True)
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='E-mail')
    address = fields.Text(string='Adresse')
    
    paiement_ids = fields.One2many('tresorerie.paiement', 'client_id', string='Paiements')
