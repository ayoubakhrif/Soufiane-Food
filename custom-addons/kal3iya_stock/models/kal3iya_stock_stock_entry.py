from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Kal3iyaStockEntry(models.Model):
    _name = 'kal3iya.stock.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Entrée Stock Kal3iya'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    product_id = fields.Many2one('kal3iya.stock.product', string='Produit', required=True)
    company_article_id = fields.Many2one('company.article', string='Article Société', related='product_id.company_article_id', store=True)
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids (Kg)')
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    
    price_purchase = fields.Float(string='Prix Achat')
    
    date = fields.Date(string='Date', required=True)
    lot = fields.Char(string='Lot', required=True)
    dum = fields.Char(string='DUM', required=True)
    calibre = fields.Char(string='Calibre')
    
    garage = fields.Selection([
        ('garage1', 'Garage 1'),
        ('garage2', 'Garage 2'),
        ('garage3', 'Garage 3'),
        ('garage4', 'Garage 4'),
        ('garage5', 'Garage 5'),
        ('garage6', 'Garage 6'),
        ('garage7', 'Garage 7'),
        ('garage8', 'Garage 8'),
        ('terrasse', 'Terrasse'),
    ], string='Garage', required=True)
    
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_kal3iya', 'Stock Kal3iya'),
    ], string='Frigo', default='stock_kal3iya')
    
    provider_id = fields.Many2one('kal3iya.stock.provider', string='Fournisseur')
    driver_id = fields.Many2one('kal3iya.stock.driver', string='Chauffeur')
    ste_id = fields.Many2one('kal3iya.stock.ste', string='Société')
    image_1920 = fields.Image(related='product_id.company_article_image', readonly=False)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)

    move_id = fields.Many2one('kal3iya.stock.move', string='Mouvement Stock', readonly=True)
    cancel_move_id = fields.Many2one('kal3iya.stock.move', string='Mouvement d\'Annulation', readonly=True)

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * rec.weight

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('kal3iya.stock.entry') or '/'
        return super(Kal3iyaStockEntry, self).create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = [
                    'product_id', 'qty', 'weight', 'price_purchase',
                    'date', 'lot', 'dum', 'garage', 'frigo', 'provider_id', 'driver_id', 'ste_id'
                ]
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les opérations confirmées ne peuvent pas être modifiées. Utilisez 'Annuler' et créez une nouvelle opération."))
        return super(Kal3iyaStockEntry, self).write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            # Create Move
            move = self.env['kal3iya.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage,
                'frigo': rec.frigo,
                'qty': rec.qty,
                'move_type': 'entry',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'price_purchase': rec.price_purchase,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'provider_id': rec.provider_id.id,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'kal3iya.stock.entry',
                'res_id': rec.id,
            })
            rec.write({
                'state': 'done',
                'move_id': move.id
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Vous ne pouvez annuler que des entrées confirmées."))
            
            # Create Reversal Move
            cancel_move = self.env['kal3iya.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage,
                'frigo': rec.frigo,
                'qty': -rec.qty,
                'move_type': 'cancel_entry',
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': rec.name,
                'price_purchase': rec.price_purchase,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'provider_id': rec.provider_id.id,
                'driver_id': rec.driver_id.id,
                'res_model': 'kal3iya.stock.entry',
                'res_id': rec.id,
                'ste_id': rec.ste_id.id,
            })
            rec.write({
                'state': 'cancel',
                'cancel_move_id': cancel_move.id
            })

    @api.constrains('qty')
    def _check_qty_positive(self):
        for rec in self:
            if rec.qty <= 0:
                raise UserError(_("La quantité doit être strictement positive."))
