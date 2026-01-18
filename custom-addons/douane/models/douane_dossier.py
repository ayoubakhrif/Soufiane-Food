from odoo import models, api

class LogistiqueDossier(models.Model):
    _inherit = 'logistique.dossier'

    def name_get(self):
        """
        Affiche le DUM si disponible et si le contexte 'show_dum' est True
        Sinon affiche le BL
        """
        result = []
        show_dum = self.env.context.get('show_dum', True)  # True par défaut = toujours afficher DUM
        
        for record in self:
            dum = False
            
            # Chercher le DUM dans les entries
            if show_dum and record.entry_ids:
                for entry in record.entry_ids:
                    if hasattr(entry, 'dum') and entry.dum:
                        dum = entry.dum
                        break
            
            # Construire le nom
            if dum:
                name = dum
            elif record.name:
                name = record.name
            else:
                name = f"Dossier #{record.id}"
            
            result.append((record.id, name))
        
        return result

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Permet de rechercher un dossier par DUM ou par BL
        """
        args = args or []
        if name:
            entries = self.env['logistique.entry'].search([
                ('dum', operator, name)
            ])
            entry_dossier_ids = entries.mapped('dossier_id').ids
            
            domain = [
                '|', '|',
                ('id', 'in', entry_dossier_ids),
                ('name', operator, name),
                ('id', '=', int(name) if name.isdigit() else 0)
            ]
            return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return super()._name_search(name, args, operator, limit, name_get_uid)