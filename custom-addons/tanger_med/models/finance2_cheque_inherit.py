from odoo import models, fields, api

class Finance2Cheque(models.Model):
    _inherit = 'finance2.cheque'

    sutra_facture_ids = fields.One2many('sutra.facture', 'cheque_id', string='Factures SUTRA liees')

    def write(self, vals):
        res = super(Finance2Cheque, self).write(vals)
        if 'date_encaissement' in vals:
            for cheque in self:
                if cheque.date_encaissement:
                    # Update related sutra factures to 'paye'
                    if cheque.sutra_facture_ids:
                        cheque.sutra_facture_ids.write({'state': 'paye'})
                else:
                    # Revert to 'encours'
                    if cheque.sutra_facture_ids:
                        cheque.sutra_facture_ids.write({'state': 'encours'})
        return res
