from odoo import models, api

class CoreSte(models.Model):
    _inherit = 'core.ste'

    @api.depends('name', 'code')
    def _compute_display_name(self):
        if self.env.context.get('display_code_only'):
            for record in self:
                record.display_name = record.code or record.name
        else:
            super()._compute_display_name()
