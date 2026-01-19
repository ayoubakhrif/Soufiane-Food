from odoo import models, fields, api

class LogistiqueDossier(models.Model):
    _inherit = 'logistique.dossier'

    # DUM Info (Moved from logistique)
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
            # entry_ids links to logistique.entry, which douane extends to add 'dum'
            entry_with_dum = record.entry_ids.filtered(lambda e: e.dum)
            if entry_with_dum:
                # Prendre le premier DUM (ou le plus récent si trié)
                record.dum = entry_with_dum[0].dum
            else:
                record.dum = False

    @api.depends('entry_ids.dum')
    def _compute_dum_ids(self):
        """Liste tous les DUMs liés au dossier (séparés par virgule)"""
        for record in self:
            dums = record.entry_ids.filtered(lambda e: e.dum).mapped('dum')
            record.dum_ids = ', '.join(dums) if dums else False

    def name_get(self):
        """
        Affiche le DUM en priorité, puis le BL
        Format: "DUM123456" ou "BL789" ou "Dossier #123"
        """
        result = []
        for record in self:
            # Priorité d'affichage: DUM > BL > ID
            if record.dum:
                name = record.dum
            elif record.name:
                name = record.name
            else:
                name = f"Dossier #{record.id}"
            
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None, order=None):
        """
        Permet de rechercher un dossier par DUM ou par BL
        Exemple: Rechercher "123" trouvera DUM123 ou BL123
        """
        args = args or []
        if name:
            # Recherche sur DUM, BL ou ID
            domain = [
                '|', '|',
                ('dum', operator, name),
                ('name', operator, name),
                ('id', '=', name if name.isdigit() else 0)
            ]
            return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid, order=order)
        return super()._name_search(name, args, operator, limit, name_get_uid, order=order)
