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

            # 1. Create Move OUT
            move_out = self.env['stock.kal3iya.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage_from,
                'qty': -rec.qty,
                'move_type': 'transfer_out', # New Type
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'stock.kal3iya.transfer',
                'res_id': rec.id,
            })

            # 2. Create Move IN
            move_in = self.env['stock.kal3iya.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage_to,
                'qty': rec.qty,
                'move_type': 'transfer_in', # New Type
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
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
                'res_model': 'stock.kal3iya.transfer',
                'res_id': rec.id,
            })

            rec.write({'state': 'cancel'})
