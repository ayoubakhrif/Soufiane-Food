from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaOtherSale(models.Model):
    _name = 'casa_hanane.other.sale'
    _description = 'Autres Ventes Stock Casa (Hanane)'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', readonly=True, default='/')
    client_id = fields.Many2one('casa_hanane.client', string='Client', required=True, tracking=True)
    product_id = fields.Many2one('casa_hanane.product', string='Produit', required=True, tracking=True)
    de_qui = fields.Char(string='De qui', tracking=True)
    
    qty = fields.Float(string='Quantité', default=1.0, tracking=True)
    weight = fields.Float(string='Poids (Kg)', default=1.0, tracking=True)
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    
    price_sale = fields.Float(string='Prix de vente', required=True, tracking=True)
    discount_amount = fields.Float(string='Réduction', default=0.0, tracking=True)
    
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    
    mt_vente = fields.Float(string='Montant Vente', compute='_compute_amounts', store=True)
    mt_vente_final = fields.Float(string='Net à Payer', compute='_compute_amounts', store=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Validé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * rec.weight

    @api.depends('tonnage', 'price_sale', 'discount_amount')
    def _compute_amounts(self):
        for rec in self:
            mt = (rec.tonnage or 0.0) * (rec.price_sale or 0.0)
            rec.mt_vente = mt
            rec.mt_vente_final = mt - (rec.discount_amount or 0.0)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa_hanane.other.sale') or '/'
        return super().create(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.write({'state': 'confirmed'})

    def action_validate(self):
        for rec in self:
            if rec.state != 'confirmed':
                continue
            rec.write({'state': 'done'})

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('confirmed', 'done'):
                continue
            rec.write({'state': 'cancel'})

    def action_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})
