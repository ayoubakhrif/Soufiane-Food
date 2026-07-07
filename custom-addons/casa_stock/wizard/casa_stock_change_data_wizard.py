from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockChangeDataWizard(models.TransientModel):
    _name = 'casa.stock.change.data.wizard'
    _description = 'Changer les données du Stock'

    stock_id = fields.Many2one('casa.stock.stock', string='Ligne de Stock', required=True, readonly=True)
    product_id = fields.Many2one('casa.product', related='stock_id.product_id', string='Produit', readonly=True)
    quantity = fields.Float(string='Quantité Restante', related='stock_id.quantity', readonly=True)
    price_purchase = fields.Float(string='Prix Achat Actuel', related='stock_id.price', readonly=True)

    # Nouveaux champs modifiables
    lot = fields.Char(string='Lot')
    calibre = fields.Char(string='Calibre')
    dum = fields.Char(string='DUM')
    weight = fields.Float(string='Poids (Kg)')
    ste_id = fields.Many2one('casa.ste', string='Société')
    stock_soufiane = fields.Boolean(string='Stock Soufiane')

    @api.model
    def default_get(self, fields_list):
        res = super(CasaStockChangeDataWizard, self).default_get(fields_list)
        stock_id = self.env.context.get('default_stock_id')
        if stock_id:
            stock = self.env['casa.stock.stock'].browse(stock_id)
            res.update({
                'lot': stock.lot,
                'calibre': stock.calibre,
                'dum': stock.dum,
                'weight': stock.weight,
                'ste_id': stock.ste_id.id if stock.ste_id else False,
                'stock_soufiane': stock.stock_soufiane,
            })
        return res

    def action_confirm(self):
        self.ensure_one()
        if self.quantity <= 0:
            raise UserError(_("La quantité restante est de 0, il n'y a pas de stock à modifier."))
            
        stock = self.stock_id
        
        # 1. Sortie avec les anciennes données
        self.env['casa.stock.move'].create({
            'product_id': stock.product_id.id,
            'lot': stock.lot,
            'dum': stock.dum,
            'scan_dum': stock.scan_dum,
            'ville': stock.ville,
            'ste_id': stock.ste_id.id,
            'weight': stock.weight,
            'calibre': stock.calibre,
            'stock_soufiane': stock.stock_soufiane,
            'qty': -self.quantity,
            'price_purchase': stock.price,
            'move_type': 'adjustment',
            'state': 'done',
            'reference': _('Modification données: Sortie (Anciennes valeurs)'),
        })
        
        # 2. Entrée avec les nouvelles données
        self.env['casa.stock.move'].create({
            'product_id': stock.product_id.id,
            'lot': self.lot,
            'dum': self.dum,
            'scan_dum': stock.scan_dum, # On garde le même scan_dum car il est lié au dum
            'ville': stock.ville, # Ville non modifiable
            'ste_id': self.ste_id.id,
            'weight': self.weight,
            'calibre': self.calibre,
            'stock_soufiane': self.stock_soufiane,
            'qty': self.quantity,
            'price_purchase': stock.price,
            'move_type': 'adjustment',
            'state': 'done',
            'reference': _('Modification données: Entrée (Nouvelles valeurs)'),
        })

        return {'type': 'ir.actions.act_window_close'}
