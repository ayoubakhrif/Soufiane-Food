from odoo import models, fields, api

class CasaClient(models.Model):
    _name = 'casa.client'
    _description = 'Clients Casa'

    name = fields.Char(string='Nom', required=True)

    exit_ids = fields.One2many(
        'casa.stock.exit',
        'client_id',
        string='Sorties'
    )

    def action_view_exits(self):
        self.ensure_one()
        return {
            'name': 'Commandes du client',
            'type': 'ir.actions.act_window',
            'res_model': 'casa.stock.exit',
            'view_mode': 'tree,form',
            'domain': [
                ('client_id', '=', self.id),
                ('state', '!=', 'cancel'),
            ],
            'context': {
                'default_client_id': self.id,
            }
        }

    exit_count = fields.Integer(
        string='Sorties',
        compute='_compute_exit_count'
    )

    @api.depends('exit_ids.state')
    def _compute_exit_count(self):
        for client in self:
            client.exit_count = len(
                client.exit_ids.filtered(lambda e: e.state == 'done')
            )
