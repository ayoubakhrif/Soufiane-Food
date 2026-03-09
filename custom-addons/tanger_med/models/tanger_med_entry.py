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

    tanger_med_lot = fields.Char(string='Lot Tanger Med')
    tanger_med_dum = fields.Char(string='DUM Tanger Med')
    destination_id = fields.Many2one('tanger.med.destination', string='Destination')

    
    @api.onchange('tanger_med_lot')
    def _onchange_tanger_med_lot(self):
        if self.tanger_med_lot and self.lot and self.tanger_med_lot != self.lot:
            return {
                'warning': {
                    'title': 'Lot Incohérent',
                    'message': f"Le Lot saisi ({self.tanger_med_lot}) est différent du Lot d'Achat ({self.lot})."
                }
            }

    @api.onchange('tanger_med_dum')
    def _onchange_tanger_med_dum(self):
        # We need to fetch the DUM from the douane entry/logistique entry based on the model inheritance
        if self.tanger_med_dum and hasattr(self, 'dum') and self.dum and self.tanger_med_dum != self.dum:
            return {
                'warning': {
                    'title': 'DUM Incohérent',
                    'message': f"La DUM saisie ({self.tanger_med_dum}) est différente de la DUM Douane ({self.dum})."
                }
            }


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
