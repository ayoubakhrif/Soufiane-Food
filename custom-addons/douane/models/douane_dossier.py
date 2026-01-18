from odoo import models, fields, api

class LogisticsDossier(models.Model):
    _inherit = 'logistique.dossier'

    # DUM Info (Added in Douane module)
    dum = fields.Char(
        string='N° DUM',
        compute='_compute_dum',
        store=True,
        help="Numéro DUM principal du dossier (récupéré depuis les entries)"
    )
    
    dum_ids = fields.Char(
        string='Tous les DUMs',
        compute='_compute_dum_ids',
        help="Liste de tous les DUMs liés à ce dossier"
    )

    @api.depends('entry_ids.dum')
    def _compute_dum(self):
        """Récupère le premier DUM trouvé dans les entries liées"""
        for record in self:
            # We can safely access .dum here because we are in the douane module
            # and logic is running on records where the field exists
            try:
                # Use filtered to find entries with a truthy dum
                entry_with_dum = record.entry_ids.filtered(lambda e: e.dum)
                if entry_with_dum:
                    record.dum = entry_with_dum[0].dum
                else:
                    record.dum = False
            except Exception:
                record.dum = False

    @api.depends('entry_ids.dum')
    def _compute_dum_ids(self):
        """Liste tous les DUMs liés au dossier (séparés par virgule)"""
        for record in self:
            try:
                dums = record.entry_ids.filtered(lambda e: e.dum).mapped('dum')
                record.dum_ids = ', '.join(dums) if dums else False
            except Exception:
                record.dum_ids = False
