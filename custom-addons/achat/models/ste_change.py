# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SteChange(models.Model):
    _name = 'ste.change'
    _description = 'Changement de Société'
    _rec_name = 'entry_id'

    entry_id = fields.Many2one('logistique.entry', string='Dossier / BL', required=True)
    old_ste_id = fields.Many2one('logistique.ste', string='Ancienne Société', readonly=True)
    new_ste_id = fields.Many2one('logistique.ste', string='Nouvelle Société', required=True)
    date_change = fields.Date(string='Date du changement', default=fields.Date.context_today, required=True)
    
    # Automatic info fields based on entry_id
    supplier_id = fields.Many2one(related='entry_id.supplier_id', string='Fournisseur', readonly=True)
    invoice_number = fields.Char(related='entry_id.invoice_number', string='Invoice Number', readonly=True)
    eta = fields.Date(related='entry_id.eta', string='ETA', readonly=True)

    @api.onchange('entry_id')
    def _onchange_entry_id(self):
        if self.entry_id:
            self.old_ste_id = self.entry_id.ste_id

    @api.model
    def create(self, vals):
        if 'entry_id' in vals and 'old_ste_id' not in vals:
            entry = self.env['logistique.entry'].browse(vals['entry_id'])
            vals['old_ste_id'] = entry.ste_id.id
            
        record = super(SteChange, self).create(vals)
        if record.entry_id and record.new_ste_id:
            old_ste_name = record.old_ste_id.name if record.old_ste_id else 'Aucune'
            new_ste_name = record.new_ste_id.name
            record.entry_id.message_post(
                body=_("Société modifiée de %s vers %s") % (old_ste_name, new_ste_name)
            )
            record.entry_id.write({'ste_id': record.new_ste_id.id})
        return record
