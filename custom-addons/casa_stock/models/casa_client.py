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
    exit_count = fields.Integer(
        string='Sorties',
        compute='_compute_exit_count'
    )

    def action_view_exits(self):
        self.ensure_one()
        return {
            'name': 'Commandes du client',
            'type': 'ir.actions.act_window',
            'res_model': 'casa.stock.exit',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id), ('state', '=', 'done'),],
            'context': {
                'default_client_id': self.id,
            }
        }
    
    @api.depends('name')
    def _compute_exit_count(self):
        for client in self:
            client.exit_count = self.env['casa.stock.exit'].search_count([
                ('client_id', '=', client.id),
                ('state', '=', 'done'),
            ])