from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockExit(models.Model):
    _name = 'casa.stock.exit'
    _description = 'Sortie Stock Casa'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    product_id = fields.Many2one('casa.product', string='Produit', required=True)
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids unit (Kg)')
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    
    price_sale = fields.Float(string='Prix Vente')
    
    date = fields.Date(string='Date', required=True)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    calibre = fields.Char(string='Calibre')
    
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', required=True)
    
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo')
    
    client_id = fields.Many2one('casa.client', string='Client')
    driver_id = fields.Many2one('casa.driver', string='Chauffeur')
    ste_id = fields.Many2one('casa.ste', string='Société')
    
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
            vals['name'] = self.env['ir.sequence'].next_by_code('casa.stock.exit') or '/'
        return super(CasaStockExit, self).create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = [
                    'product_id', 'qty', 'weight', 'price_sale',
                    'date', 'lot', 'dum', 'ville', 'frigo', 'client_id', 'driver_id', 'ste_id'
                ]
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les opérations confirmées ne peuvent pas être modifiées. Utilisez 'Annuler' et créez une nouvelle opération."))
        return super(CasaStockExit, self).write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            # Optimized availability check using read_group
            domain = [
                ('product_id', '=', rec.product_id.id),
                ('lot', '=', rec.lot),
                ('dum', '=', rec.dum),
                ('ville', '=', rec.ville),
                ('frigo', '=', rec.frigo),
                ('state', '=', 'done')
            ]
            res = self.env['casa.stock.move'].read_group(domain, ['qty'], [])
            total_available = res[0]['qty'] if res and res[0]['qty'] else 0.0
            
            if rec.qty > total_available:
                raise UserError(_("Stock insuffisant ! Disponible : %s, Demandé : %s") % (total_available, rec.qty))
            
            # Create Move
            move = self.env['casa.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'frigo': rec.frigo,
                'qty': -rec.qty,
                'move_type': 'exit',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'price_sale': rec.price_sale,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'casa.stock.exit',
                'res_id': rec.id,
            })
            rec.write({
                'state': 'done',
                'move_id': move.id
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Vous ne pouvez annuler que des sorties confirmées."))
            
            # Create Reversal Move
            cancel_move = self.env['casa.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'frigo': rec.frigo,
                'qty': rec.qty,
                'move_type': 'cancel_exit',
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': rec.name,
                'price_sale': rec.price_sale,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'res_model': 'casa.stock.exit',
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
                raise UserError(_("La quantité doit être strictement positive."))
