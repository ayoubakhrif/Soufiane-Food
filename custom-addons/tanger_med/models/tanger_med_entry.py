from odoo import models, fields, api


class TangerMedEntry(models.Model):
    _inherit = 'logistique.entry'

    sur_mag_amount = fields.Float(string='SUR+MAG')
    sur_mag_date = fields.Date(string='SUR+MAG Date', readonly=True)
    sur_mag_user = fields.Many2one(
        'res.users',
        string='SUR+MAG Saisi par',
        readonly=True,
    )

    @api.onchange('sur_mag_amount')
    def _onchange_sur_mag_amount(self):
        if self.sur_mag_amount:
            self.sur_mag_date = fields.Date.context_today(self)
            self.sur_mag_user = self.env.user
        else:
            self.sur_mag_date = False
            self.sur_mag_user = False

    def write(self, vals):
        res = super().write(vals)
        if 'sur_mag_amount' in vals:
            if vals['sur_mag_amount']:
                super().write({
                    'sur_mag_date': fields.Date.context_today(self),
                    'sur_mag_user': self.env.user.id,
                })
            else:
                super().write({
                    'sur_mag_date': False,
                    'sur_mag_user': False,
                })
        return res
