from odoo import models, fields, api

class Kal3iyaStockAgent(models.Model):
    _name = 'kal3iya.stock.agent'
    _description = 'Agent de Stock Kal3iya'
    _order = 'name'

    name = fields.Char(string='Nom de l''agent', required=True)
    phone = fields.Char(string='Numéro de téléphone (Identifiant)', required=True, index=True)
    password = fields.Char(string='Mot de passe', required=True)
    active = fields.Boolean(string='Actif', default=True)
    notes = fields.Text(string='Remarques')

    _sql_constraints = [
        ('phone_unique', 'unique(phone)', 'Ce numéro de téléphone est déjà attribué à un autre agent !')
    ]
