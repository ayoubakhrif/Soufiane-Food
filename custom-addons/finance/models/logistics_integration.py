from odoo import models, api

class LogistiqueEntry(models.Model):
    _inherit = 'logistique.entry'

    @api.model
    def create(self, vals):
        # Create the standard logistique entry
        record = super(LogistiqueEntry, self).create(vals)
        
        # AUTOMATICALLY CREATE SUTRA RECORD
        # We wrap this in a try-except block just in case, though it should work.
        # This ensures every new logistics/douane entry has a corresponding Sutra record.
        # SUTRA: Manual creation now required (Refactor Jan 2026)
        # self.env['finance.sutra'].create({
        #     'douane_id': record.id,
        # })
        
        # MARGLORY: Keeps auto-creation for now
        self.env['finance.marglory'].sudo().create({
            'douane_id': record.id,
        })
        
        return record
