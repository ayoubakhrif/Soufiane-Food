from odoo import models, fields, api

class Finance2Cheque(models.Model):
    _inherit = 'finance2.cheque'

    sutra_facture_ids = fields.One2many('sutra.facture', 'cheque_id', string='Factures SUTRA liees')
    is_sutra_benif = fields.Boolean(compute='_compute_is_sutra_benif')

    @api.depends('benif_id', 'benif_id.name')
    def _compute_is_sutra_benif(self):
        for rec in self:
            rec.is_sutra_benif = bool(rec.benif_id and rec.benif_id.name and 'sutra' in rec.benif_id.name.lower())


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
