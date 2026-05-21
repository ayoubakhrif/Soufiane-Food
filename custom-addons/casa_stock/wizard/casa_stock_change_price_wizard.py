from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockChangePriceWizard(models.TransientModel):
    _name = 'casa.stock.change.price.wizard'
    _description = 'Changer le Prix d\'Achat du Stock'

    stock_id = fields.Many2one('casa.stock.stock', string='Ligne de Stock', required=True, readonly=True)
    product_id = fields.Many2one('casa.product', related='stock_id.product_id', string='Produit', readonly=True)
    current_price = fields.Float(string='Prix Actuel', related='stock_id.price', readonly=True)
    new_price = fields.Float(string='Nouveau Prix', required=True)
    quantity = fields.Float(string='Quantité Restante', related='stock_id.quantity', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        if self.new_price <= 0:
            raise UserError(_("Le nouveau prix doit être supérieur à 0."))
        if self.quantity <= 0:
            raise UserError(_("La quantité restante est de 0, il n'y a pas de stock à réévaluer."))
            
        stock = self.stock_id
        
        # 1. Déduction de la quantité au prix actuel (Mouvement d'Ajustement Négatif)
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
            'price_purchase': self.current_price,
            'move_type': 'adjustment',
            'state': 'done',
            'reference': _('Réévaluation Prix: Sortie (Ancien Prix)'),
        })
        
        # 2. Ajout de la même quantité au nouveau prix (Mouvement d'Ajustement Positif)
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
            'qty': self.quantity,
            'price_purchase': self.new_price,
            'move_type': 'adjustment',
            'state': 'done',
            'reference': _('Réévaluation Prix: Entrée (Nouveau Prix)'),
        })

        return {'type': 'ir.actions.act_window_close'}
