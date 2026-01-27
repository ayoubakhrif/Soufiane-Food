from odoo import models, fields

class LogistiqueSte(models.Model):
    _inherit = 'logistique.ste'

    core_ste_id = fields.Many2one('core.ste', string='Société (Données Centralisées)')
