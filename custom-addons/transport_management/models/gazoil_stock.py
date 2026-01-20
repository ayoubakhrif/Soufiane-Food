from odoo import models, fields, api

class GasoilStock(models.Model):
    _name = 'gasoil.stock'
    _description = 'Gasoil Stock'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Stock',
        default='Stock Gasoil',
        readonly=True
    )

    total_liters_in = fields.Float(
        string='Total Entrées (Litres)',
        compute='_compute_stock',
        store=True
    )

    total_liters_out = fields.Float(
        string='Total Sorties (Litres)',
        compute='_compute_stock',
        store=True
    )

    remaining_liters = fields.Float(
        string='Reste Gasoil (Litres)',
        compute='_compute_stock',
        store=True,
        tracking=True
    )

    last_purchase_price = fields.Float(
        string='Dernier Prix Achat / Litre',
        compute='_compute_stock',
        store=True
    )

    stock_value = fields.Float(
        string='Valeur du stock',
        compute='_compute_stock',
        store=True
    )

    @api.depends(
        'total_liters_in',
        'total_liters_out'
    )
    def _compute_stock(self):
        Refill = self.env['gasoil.refill']
        Sale = self.env['gasoil.sale']

        for rec in self:
            total_in = sum(Refill.search([]).mapped('liters'))
            total_out = sum(Sale.search([]).mapped('liters'))

            rec.total_liters_in = total_in
            rec.total_liters_out = total_out
            rec.remaining_liters = total_in - total_out

            last_refill = Refill.search([], order='date desc', limit=1)
            rec.last_purchase_price = last_refill.purchase_price if last_refill else 0.0

            rec.stock_value = rec.remaining_liters * rec.last_purchase_price

    @api.model
    def get_stock(self):
        stock = self.search([], limit=1)
        if not stock:
            stock = self.create({})
        return stock