from odoo import models, fields

class Kal3iyaStockClient(models.Model):
    _name = 'kal3iya.stock.client'
    _description = 'Clients Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)

    exit_ids = fields.One2many(
        'kal3iya.stock.exit',
        'client_id',
        string='Sorties'
    )
    
    return_ids = fields.One2many(
        'kal3iya.stock.return',
        'client_id',
        string='Retours'
    )

    def action_view_exits(self):
        self.ensure_one()
        return {
            'name': 'Commandes du client',
            'type': 'ir.actions.act_window',
            'res_model': 'kal3iya.stock.exit',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'context': {
                'default_client_id': self.id,
            }
        }