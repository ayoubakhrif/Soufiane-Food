from odoo import models, fields

class CasaStockClient(models.Model):
    _name = 'casa_field.stock.client'
    _description = 'Clients Stock Casa'

    name = fields.Char(string='Nom', required=True)

    exit_ids = fields.One2many(
        'casa_field.stock.exit',
        'client_id',
        string='Sorties'
    )
    
    return_ids = fields.One2many(
        'casa_field.stock.return',
        'client_id',
        string='Retours'
    )

    def action_view_exits(self):
        self.ensure_one()
        return {
            'name': 'Commandes du client',
            'type': 'ir.actions.act_window',
            'res_model': 'casa_field.stock.exit',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'context': {
                'default_client_id': self.id,
            }
        }
