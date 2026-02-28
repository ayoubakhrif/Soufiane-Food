from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockKal3iyaTransfer(models.Model):
    _name = 'stock.kal3iya.transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Transfert Inter-Garage'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    
    product_id = fields.Many2one('stock.kal3iya.product', string='Produit', required=True)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    
    qty = fields.Float(string='Quantité', required=True)
    
    garage_from = fields.Selection([
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
    ], string='Garage Départ', required=True)

    garage_to = fields.Selection([
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
    ], string='Garage Arrivée', required=True)
    
    driver_id = fields.Many2one('stock.kal3iya.driver', string='Chauffeur')
    ste_id = fields.Many2one('stock.kal3iya.ste', string='Société')
    weight = fields.Float(string='Poids (Kg)')
    calibre = fields.Char(string='Calibre')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', track_visibility='onchange')

    move_out_id = fields.Many2one('stock.kal3iya.move', string='Mouvement Sortant', readonly=True)
    move_in_id = fields.Many2one('stock.kal3iya.move', string='Mouvement Entrant', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.kal3iya.transfer') or '/'
        return super(StockKal3iyaTransfer, self).create(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            if rec.garage_from == rec.garage_to:
                raise UserError(_("Le garage de départ et d'arrivée doivent être différents."))

            # Resolve Stock Info from Source (to ensure deduction instead of new line)
            # Find the existing stock line to get the correct DUM, STE if not provided
            # User REQUIRES matching by Weight as well.
            domain = [
                ('product_id', '=', rec.product_id.id),
                ('lot', '=', rec.lot),
                ('garage', '=', rec.garage_from),
            ]
            
            # If weight is provided or even if 0, we try to match it if we want strict deduction.
            # However, floating point comparison can be tricky.
            # Let's assume strict equality for now as requested.
            domain.append(('weight', '=', rec.weight))

            if rec.dum:
                domain.append(('dum', '=', rec.dum))
            
            # Search strictly first
            stock_line = self.env['stock.kal3iya.stock'].search(domain, limit=1)
            
            val_dum = rec.dum
            val_ste_id = rec.ste_id.id
            val_weight = rec.weight # We use the transfer's weight, which matched the stock line
            
            if stock_line:
                if not val_dum:
                    val_dum = stock_line.dum
                if not val_ste_id:
                    val_ste_id = stock_line.ste_id.id
                # Weight matches, so we don't need to "fill" it from stock line, 
                # but valid to ensure we have it if transfer was 0 but matched 0? 
                # If transfer has weight 0, and we found a line with weight 0, then val_weight is 0.
                # If transfer has weight 10, found line with 10, val_weight is 10.
            
            # 1. Create Move OUT
            move_out = self.env['stock.kal3iya.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': val_dum,
                'garage': rec.garage_from,
                'qty': -rec.qty,
                'move_type': 'transfer_out', # New Type
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'driver_id': rec.driver_id.id,
                'weight': val_weight,
                'calibre': rec.calibre,
                'ste_id': val_ste_id,
                'res_model': 'stock.kal3iya.transfer',
                'res_id': rec.id,
            })

            # 2. Create Move IN
            move_in = self.env['stock.kal3iya.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': val_dum, # Keep same DUM
                'garage': rec.garage_to,
                'qty': rec.qty,
                'move_type': 'transfer_in', # New Type
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'weight': val_weight,
                'calibre': rec.calibre,
                'driver_id': rec.driver_id.id,
                'ste_id': val_ste_id,
                'res_model': 'stock.kal3iya.transfer',
                'res_id': rec.id,
            })

            rec.write({
                'state': 'done',
                'move_out_id': move_out.id,
                'move_in_id': move_in.id,
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Seuls les transferts confirmés peuvent être annulés."))

            # Reverse the movements
            # 1. Reverse OUT (Create +Qty at garage_from)
            self.env['stock.kal3iya.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage_from,
                'qty': rec.qty, # Positive
                'move_type': 'transfer_out', # Keep type for traceability or use specific cancel type? 
                                             # Plan said "Reverse moves". 
                                             # Using same type allows filtering "Transfer Out" to see net flow = 0.
                                             # Or maybe better to use adjustment? 
                                             # Let's stick to "transfer_out" but positive.
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': f"{rec.name} (Annulation)",
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'weight': rec.weight,
                'res_model': 'stock.kal3iya.transfer',
                'res_id': rec.id,
            })

            # 2. Reverse IN (Create -Qty at garage_to)
            self.env['stock.kal3iya.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage_to,
                'qty': -rec.qty, # Negative
                'move_type': 'transfer_in',
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': f"{rec.name} (Annulation)",
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'weight': rec.weight,
                'res_model': 'stock.kal3iya.transfer',
                'res_id': rec.id,
            })

            rec.write({'state': 'cancel'})
