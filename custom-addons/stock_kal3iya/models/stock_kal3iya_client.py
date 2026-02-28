from odoo import models, fields

class StockKal3iyaClient(models.Model):
    _name = 'stock.kal3iya.client'
    _description = 'Clients Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)

    exit_ids = fields.One2many(
        'stock.kal3iya.exit',
        'client_id',
        string='Sorties'
    )
    
    return_ids = fields.One2many(
        'stock.kal3iya.return',
        'client_id',
        string='Retours'
    )

    def action_view_exits(self):
        self.ensure_one()
        return {
            'name': 'Commandes du client',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.kal3iya.exit',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'context': {
                'default_client_id': self.id,
            }
        }


