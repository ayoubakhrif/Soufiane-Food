# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

INCOTERM_SELECTION = [
    ('cfr', 'CFR'),
    ('fob', 'FOB'),
    ('emirate', 'EMIRATE'),
    ('exw', 'EXW'),
]

class SteChange(models.Model):
    _name = 'ste.change'
    _description = 'Changement de Société / Incoterm'
    _rec_name = 'entry_id'

    entry_id = fields.Many2one('logistique.entry', string='Dossier / BL', required=True)

    # Société
    old_ste_id = fields.Many2one('logistique.ste', string='Ancienne Société', readonly=True)
    new_ste_id = fields.Many2one('logistique.ste', string='Nouvelle Société')

    # Incoterm
    old_incoterm = fields.Selection(INCOTERM_SELECTION, string='Ancien Incoterm', readonly=True)
    new_incoterm = fields.Selection(INCOTERM_SELECTION, string='Nouvel Incoterm')

    date_change = fields.Date(string='Date du changement', default=fields.Date.context_today, required=True)

    # Automatic info fields based on entry_id
    supplier_id = fields.Many2one(related='entry_id.supplier_id', string='Fournisseur', readonly=True)
    invoice_number = fields.Char(related='entry_id.invoice_number', string='Invoice Number', readonly=True)
    eta = fields.Date(related='entry_id.eta', string='ETA', readonly=True)

    @api.onchange('entry_id')
    def _onchange_entry_id(self):
        if self.entry_id:
            self.old_ste_id = self.entry_id.ste_id
            self.old_incoterm = self.entry_id.incoterm

    @api.constrains('new_ste_id', 'old_ste_id', 'new_incoterm', 'old_incoterm')
    def _check_no_real_change(self):
        for rec in self:
            if rec.new_ste_id and rec.new_ste_id == rec.old_ste_id:
                raise ValidationError(
                    _("La nouvelle société est identique à l'ancienne. Aucun changement effectué.")
                )
            if rec.new_incoterm and rec.new_incoterm == rec.old_incoterm:
                raise ValidationError(
                    _("Le nouvel incoterm est identique à l'ancien. Aucun changement effectué.")
                )

    @api.model
    def create(self, vals):
        if 'entry_id' in vals:
            entry = self.env['logistique.entry'].browse(vals['entry_id'])
            if 'old_ste_id' not in vals:
                vals['old_ste_id'] = entry.ste_id.id
            if 'old_incoterm' not in vals:
                vals['old_incoterm'] = entry.incoterm

        record = super(SteChange, self).create(vals)

        entry = record.entry_id
        if not entry:
            return record

        entry_vals = {}
        msg_parts = []

        # Société
        if record.new_ste_id:
            old_ste_name = record.old_ste_id.name if record.old_ste_id else 'Aucune'
            new_ste_name = record.new_ste_id.name
            entry_vals['ste_id'] = record.new_ste_id.id
            msg_parts.append(_("Société modifiée de %s vers %s") % (old_ste_name, new_ste_name))

        # Incoterm
        if record.new_incoterm:
            old_inc = dict(INCOTERM_SELECTION).get(record.old_incoterm, 'Aucun')
            new_inc = dict(INCOTERM_SELECTION).get(record.new_incoterm, '')
            entry_vals['incoterm'] = record.new_incoterm
            msg_parts.append(_("Incoterm modifié de %s vers %s") % (old_inc, new_inc))

        if entry_vals:
            entry.write(entry_vals)
            if entry.contract_id:
                contract_vals = {}
                if 'ste_id' in entry_vals:
                    contract_vals['ste_id'] = entry_vals['ste_id']
                if 'incoterm' in entry_vals:
                    contract_vals['incoterm'] = entry_vals['incoterm']
                if contract_vals:
                    entry.contract_id.write(contract_vals)

        if msg_parts:
            entry.message_post(body='<br/>'.join(msg_parts))

        return record
