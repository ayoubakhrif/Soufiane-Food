from odoo import models, fields

class TransportDriverAlias(models.Model):
    _name = 'transport.driver.alias'
    _description = 'Alias Chauffeur'

    name = fields.Char(string='Alias', required=True)
    driver_id = fields.Many2one('transport.driver', string='Chauffeur', ondelete='cascade', required=True)
