from odoo import models, fields, api

class CasaClient(models.Model):
    _name = 'casa.client'
    _description = 'Clients Casa'

    name = fields.Char(string='Nom', required=True)

    # Champ computed pour le nombre de commandes
    exit_count = fields.Integer(
        string='Commandes',
        compute='_compute_exit_count',
    )

    # ⚠️ NE PAS ajouter exit_ids en One2many si vous ne voulez pas de vue inline
    # Le champ existe déjà via la relation inverse dans casa.stock.exit

    @api.depends('name')  # Dépendance factice pour forcer le recalcul
    def _compute_exit_count(self):
        """Compte uniquement les sorties confirmées (done)"""
        for rec in self:
            rec.exit_count = self.env['casa.stock.exit'].search_count([
                ('client_id', '=', rec.id),
                ('state', '=', 'done')
            ])

    def action_view_exits(self):
        """Action pour afficher les sorties du client"""
        self.ensure_one()
        return {
            'name': f'Commandes de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'casa.stock.exit',
            'view_mode': 'tree,form',
            'domain': [
                ('client_id', '=', self.id),
                ('state', '!=', 'cancel'),
            ],
            'context': {
                'default_client_id': self.id,
                'search_default_group_by_date': 1,
            },
        }