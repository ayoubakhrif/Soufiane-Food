from odoo import models, fields, api

class GasoilRefill(models.Model):
    _name = 'gasoil.refill'
    _description = 'Gasoil Refill'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'date'

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    liters = fields.Float(
        string='Quantité (Litres)',
        required=True,
        tracking=True
    )
    purchase_price = fields.Float(
        string='Prix d’achat / Litre',
        required=True,
        tracking=True
    )

    total_cost = fields.Float(
        string='Coût total',
        compute='_compute_total_cost',
        store=True
    )

    @api.depends('liters', 'purchase_price')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = (rec.liters or 0.0) * (rec.purchase_price or 0.0)

