from odoo import models, fields, api

class CasaSale(models.Model):
    _name = 'casa.sale'
    _description = 'Vente Commerciale'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Link to Logistics (Source of Truth for Stock)
    stock_exit_id = fields.Many2one('casa.stock.exit', string='Sortie Stock Origine', readonly=True, ondelete='cascade')
    
    # Identifying Info (Copied for performance/independence)
    product_id = fields.Many2one('casa.product', string='Produit', required=True, readonly=True)
    client_id = fields.Many2one('casa.client', string='Client', required=True, readonly=True)
    ste_id = fields.Many2one('casa.ste', string='Société', readonly=True)
    lot = fields.Char(string='Lot', readonly=True)
    dum = fields.Char(string='DUM', readonly=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', readonly=True)
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo', readonly=True)

    # Initial Data (From Stock)
    quantity = fields.Float(string='Quantité', readonly=True)
    weight = fields.Float(string='Poids (Kg)', readonly=True)
    tonnage = fields.Float(string='Tonnage Initial', readonly=True)
    selling_price = fields.Float(string='Prix de Vente Initial', readonly=True)
    mt_vente = fields.Float(string='Montant Initial', readonly=True)
    date = fields.Date(string='Date', required=True, readonly=True)
    week = fields.Char(string='Semaine', compute='_compute_week', store=True)

    # Financial Adjustments (Editable Commercial Data)
    selling_price_final = fields.Float(string='Prix Final', tracking=True)
    tonnage_final = fields.Float(string='Tonnage Final', tracking=True)
    mt_vente_final = fields.Float(string='Montant Final', compute='_compute_mt_vente_final', store=True)

    @api.depends('date')
    def _compute_week(self):
        for rec in self:
            if rec.date:
                rec.week = rec.date.strftime("%Y-W%W")
            else:
                rec.week = False

    @api.depends('selling_price_final', 'tonnage_final', 'mt_vente')
    def _compute_mt_vente_final(self):
        for rec in self:
            # Logic: Use final values if present, else fallback to initial
            price = rec.selling_price_final or rec.selling_price
            tonnage = rec.tonnage_final or rec.tonnage
            
            # If nothing changed, we can either set it to initial or handle logic
            # Here we follow Kal3iya logic: mt_final is the effective amount due
            rec.mt_vente_final = price * tonnage

    def open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'casa.sale',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
