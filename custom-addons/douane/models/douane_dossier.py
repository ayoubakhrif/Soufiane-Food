from odoo import models, fields, api

class LogistiqueDossier(models.Model):
    _inherit = 'logistique.dossier'

    # DUM Info
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
            # We access entry_ids.dum. dum field exists on logistique.entry 
            # because this file is in douane module which extends logistique.entry
            entry_with_dum = record.entry_ids.filtered(lambda e: e.dum)
            if entry_with_dum:
                record.dum = entry_with_dum[0].dum
            else:
                record.dum = False

    @api.depends('entry_ids.dum')
    def _compute_dum_ids(self):
        """Liste tous les DUMs liés au dossier"""
        for record in self:
            dums = record.entry_ids.filtered(lambda e: e.dum).mapped('dum')
            record.dum_ids = ', '.join(dums) if dums else False

    def name_get(self):
        """
        Affiche le DUM en priorité si demandé par contexte ou si c'est la seule info pertinente?
        Le user voulait: "If context show_dum=True -> display dum".
        """
        result = []
        for record in self:
            name = record.name or f"Dossier #{record.id}"
            
            # Prioritize DUM if context requests it
            if self.env.context.get('show_dum') and record.dum:
                name = record.dum
                
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None, order=None):
        if name and self.env.context.get('show_dum'):
             args = args or []
             domain = [('dum', operator, name)]
             return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        
        # Fallback to standard search (BL, ID, etc)
        return super(LogistiqueDossier, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid, order=order)
