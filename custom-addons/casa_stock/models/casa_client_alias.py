from odoo import models, fields

class CasaClientAlias(models.Model):
    _name = 'casa.client.alias'
    _description = 'Client Alias for WhatsApp'

    name = fields.Char(string='Alias', required=True)
    client_id = fields.Many2one('casa.client', string='Client', ondelete='cascade')

class CasaClient(models.Model):
    _inherit = 'casa.client'

    alias_ids = fields.One2many('casa.client.alias', 'client_id', string='Alias')
