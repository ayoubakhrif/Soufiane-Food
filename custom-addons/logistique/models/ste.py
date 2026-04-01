from odoo import models, fields

class LogistiqueSte(models.Model):
    _name = 'logistique.ste'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Société'

    name = fields.Char(string='Nom', required=True, tracking=True)
    core_ste_id = fields.Many2one('core.ste', string='Société (Source)', tracking=True)
    is_zone_franche = fields.Boolean(related='core_ste_id.is_zone_franche', string='Zone Franche', readonly=True, store=True, tracking=True)
