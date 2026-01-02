from odoo import models, fields, api

class CasaSaleReturn(models.Model):
    _name = 'casa.sale.return'
    _description = 'Retour Commercial'
    _order = 'date desc'

    # Link to Logistics
    stock_entry_id = fields.Many2one('casa.stock.entry', string='Entrée Stock Origine', readonly=True, ondelete='cascade')

    product_id = fields.Many2one('casa.product', string='Produit', required=True, readonly=True)
    client_id = fields.Many2one('casa.client', string='Client', required=True, readonly=True)
    ste_id = fields.Many2one('casa.ste', string='Société', readonly=True)
    
    quantity = fields.Float(string='Quantité', readonly=True)
    weight = fields.Float(string='Poids (Kg)', readonly=True)
    tonnage = fields.Float(string='Tonnage', readonly=True)
    
    # Financials
    price_unit = fields.Float(string='Prix Unitaire', required=True)
    amount = fields.Float(string='Montant', compute='_compute_amount', store=True)
    
    date = fields.Date(string='Date', required=True, readonly=True)
    week = fields.Char(string='Semaine', compute='_compute_week', store=True)

    @api.depends('date')
    def _compute_week(self):
        for rec in self:
            if rec.date:
                rec.week = rec.date.strftime("%Y-W%W")
            else:
                rec.week = False

    @api.depends('price_unit', 'tonnage')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.price_unit * rec.tonnage
