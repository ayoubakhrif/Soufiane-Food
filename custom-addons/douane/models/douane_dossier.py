from odoo import models, api

class LogistiqueDossier(models.Model):
    _inherit = 'logistique.dossier'

    def name_get(self):
        """
        Affiche le DUM en priorité, puis le BL
        Cherche le DUM directement dans les entries sans champ stocké
        """
        result = []
        for record in self:
            # Chercher un DUM dans les entries liées
            dum = False
            for entry in record.entry_ids:
                if hasattr(entry, 'dum') and entry.dum:
                    dum = entry.dum
                    break
            
            # Afficher DUM > BL > ID
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
            # Rechercher dans les entries qui ont un DUM
            entry_ids = self.env['logistique.entry'].search([
                ('dum', operator, name)
            ]).mapped('dossier_id').ids
            
            # Combiner avec recherche sur BL
            domain = [
                '|', '|',
                ('id', 'in', entry_ids),
                ('name', operator, name),
                ('id', '=', int(name) if name.isdigit() else 0)
            ]
            return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return super()._name_search(name, args, operator, limit, name_get_uid)