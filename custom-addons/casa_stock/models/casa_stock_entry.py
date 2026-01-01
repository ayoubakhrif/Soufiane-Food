from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockEntry(models.Model):
    _name = 'casa.stock.entry'
    _description = 'Entrée Stock Casa'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    product_id = fields.Many2one('casa.product', string='Produit', required=True)
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids (Kg)')
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    
    price_purchase = fields.Float(string='Prix Achat')
    price_sale = fields.Float(string='Prix Vente')
    
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    calibre = fields.Char(string='Calibre')
    
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', required=True, default='casa')
    
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo', default='stock_casa')
    
    provider_id = fields.Many2one('casa.provider', string='Fournisseur')
    driver_id = fields.Many2one('casa.driver', string='Chauffeur')
    image_1920 = fields.Image(related='product_id.image_1920', readonly=False)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)

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

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            # Create Move
            move = self.env['casa.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'frigo': rec.frigo,
                'qty': rec.qty,
                'move_type': 'entry',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'price_purchase': rec.price_purchase,
                'price_sale': rec.price_sale,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'provider_id': rec.provider_id.id,
                'driver_id': rec.driver_id.id,
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
            cancel_move = self.env['casa.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'frigo': rec.frigo,
                'qty': -rec.qty,
                'move_type': 'cancel_entry',
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': rec.name,
                'price_purchase': rec.price_purchase,
                'price_sale': rec.price_sale,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'provider_id': rec.provider_id.id,
                'driver_id': rec.driver_id.id,
            })
            rec.write({
                'state': 'cancel',
                'cancel_move_id': cancel_move.id
            })
