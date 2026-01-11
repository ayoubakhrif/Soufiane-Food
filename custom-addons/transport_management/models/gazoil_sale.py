from odoo import models, fields, api
class GasoilSale(models.Model):
    _name = 'gasoil.sale'
    _description = 'Gasoil Sale'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'date'

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    driver = fields.Char(string='Chauffeur', required=True, tracking=True)

    client = fields.Selection([
        ('chair', 'Chair'),
        ('soufiane', 'Soufiane'),
        ('remorque', 'Remorque'),
    ], string='Client', required=True, tracking=True)

    amount = fields.Float(
        string='Montant',
        required=True,
        tracking=True
    )

    purchase_price = fields.Float(
        string="Prix de vente / Litre",
        readonly=True,
        tracking=True
    )

    sale_price = fields.Float(
        string='Prix de vente / Litre',
        required=True,
        tracking=True
    )

    liters = fields.Float(
        string='Litrage',
        compute='_compute_liters',
        store=True
    )

    profit = fields.Float(
        string='Bénéfice',
        compute='_compute_profit',
        store=True,
        tracking=True
    )

    # 🔹 Dernier prix d’achat automatiquement
    @api.model
    def create(self, vals):
        last_refill = self.env['gasoil.refill'].search([], order='date desc', limit=1)
        if last_refill:
            vals['purchase_price'] = last_refill.purchase_price
        return super().create(vals)

    @api.depends('amount', 'purchase_price')
    def _compute_liters(self):
        for rec in self:
            if rec.sale_price:
                rec.liters = rec.amount / rec.sale_price
            else:
                rec.liters = 0.0

    @api.depends('amount', 'liters', 'purchase_price')
    def _compute_profit(self):
        for rec in self:
            cost = rec.liters * rec.purchase_price
            rec.profit = rec.amount - cost