from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockEntry(models.Model):
    ste_id = fields.Integer(string='Ancienne Societe (A ignorer)')
    _name = 'casa.stock.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'EntrÃ©e Stock Casa'
    _order = 'date desc, id desc'

    name = fields.Char(string='RÃ©fÃ©rence', readonly=True, default='/')
    product_id = fields.Many2one('casa.stock.product', string='Produit', required=True)
    company_article_id = fields.Many2one('company.article', string='Article SociÃ©tÃ©', related='product_id.company_article_id', store=True)
    qty = fields.Float(string='QuantitÃ©', required=True)
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
        ('fenidek', 'Fenidek'),
    ], string='Garage', required=True)
    
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo', default='stock_casa')
    
    driver_id = fields.Many2one('casa.stock.driver', string='Chauffeur')
    image_1920 = fields.Image(related='product_id.company_article_image', readonly=False)
    photo_packaging = fields.Binary(string='Photo Emballage', attachment=True)
    photo_container = fields.Binary(string='Photo Conteneur', attachment=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'ConfirmÃ©'),
        ('cancel', 'AnnulÃ©'),
    ], string='Ã‰tat', default='draft', required=True)

    move_id = fields.Many2one('casa.stock.move', string='Mouvement Stock', readonly=True)
    cancel_move_id = fields.Many2one('casa.stock.move', string='Mouvement d\'Annulation', readonly=True)

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * rec.weight

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa.stock.entry') or '/'
        return super(CasaStockEntry, self).create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = [
                    'product_id', 'qty', 'weight', 'price_purchase',
                    'date', 'lot', 'dum', 'garage', 'frigo', 'driver_id'
                ]
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les opÃ©rations confirmÃ©es ne peuvent pas Ãªtre modifiÃ©es. Utilisez 'Annuler' et crÃ©ez une nouvelle opÃ©ration."))
        return super(CasaStockEntry, self).write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            # Create Move
            move = self.env['casa.stock.move'].create({
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
                'driver_id': rec.driver_id.id,
                'res_model': 'casa.stock.entry',
                'res_id': rec.id,
            })
            rec.write({
                'state': 'done',
                'move_id': move.id
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Vous ne pouvez annuler que des entrÃ©es confirmÃ©es."))
            
            # Create Reversal Move
            cancel_move = self.env['casa.stock.move'].create({
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
                'driver_id': rec.driver_id.id,
                'res_model': 'casa.stock.entry',
                'res_id': rec.id,
            })
            rec.write({
                'state': 'cancel',
                'cancel_move_id': cancel_move.id
            })

    @api.constrains('qty')
    def _check_qty_positive(self):
        for rec in self:
            if rec.qty <= 0:
                raise UserError(_("La quantitÃ© doit Ãªtre strictement positive."))


