from odoo import models, fields

class CasaStockAgent(models.Model):
    _name = 'casa_field.stock.agent'
    _description = 'Agents de Stock Casa'

    name = fields.Char(string='Nom', required=True)
    phone = fields.Char(string='TÃ©lÃ©phone', required=True)
    password = fields.Char(string='Mot de passe', required=True)
    role = fields.Selection([
        ('agent', 'Agent de Stock'),
        ('commercial', 'Commercial')
    ], string='RÃ´le', default='agent', required=True)
    active = fields.Boolean(string='Actif', default=True)
