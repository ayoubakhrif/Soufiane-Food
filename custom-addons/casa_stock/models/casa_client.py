from odoo import models, fields, api

class CasaClient(models.Model):
    _name = 'casa.client'
    _description = 'Clients Casa'

    name = fields.Char(string='Nom', required=True)

    exit_count = fields.Integer(
        string='Commandes',
        compute='_compute_exit_count'
    )

    @api.depends('exit_ids.state')
    def _compute_exit_count(self):
        for client in self:
            client.exit_count = len(
                client.exit_ids.filtered(lambda e: e.state == 'done')
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
        }
