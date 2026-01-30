from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Kal3iyaStockExit(models.Model):
    _name = 'kal3iya.stock.exit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sortie Stock Kal3iya'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    product_id = fields.Many2one('kal3iya.stock.product', string='Produit', required=True)
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids unit (Kg)')
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    

    
    date = fields.Date(string='Date', required=True)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
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
        ('stock_kal3iya', 'Stock Kal3iya'),
    ], string='Frigo')
    
    client_id = fields.Many2one('kal3iya.stock.client', string='Client')
    driver_id = fields.Many2one('kal3iya.stock.driver', string='Chauffeur')
    ste_id = fields.Many2one('kal3iya.stock.ste', string='Société')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)

    move_id = fields.Many2one('kal3iya.stock.move', string='Mouvement Stock', readonly=True)
    cancel_move_id = fields.Many2one('kal3iya.stock.move', string='Mouvement d\'Annulation', readonly=True)

    return_ids = fields.One2many('kal3iya.stock.return', 'exit_id', string='Retours')
    returned_qty = fields.Float(string='Quantité Retournée', compute='_compute_returned_qty', store=True)

    @api.depends('return_ids.qty', 'return_ids.state')
    def _compute_returned_qty(self):
        for rec in self:
            rec.returned_qty = sum(rec.return_ids.filtered(lambda r: r.state == 'done').mapped('qty'))

    def action_new_return(self):
        self.ensure_one()
        return {
            'name': 'Nouveau Retour',
            'type': 'ir.actions.act_window',
            'res_model': 'kal3iya.stock.return',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_exit_id': self.id,
                'default_driver_id': self.driver_id.id,
            }
        }

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * rec.weight

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('kal3iya.stock.exit') or '/'
        return super(Kal3iyaStockExit, self).create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = [
                    'product_id', 'qty', 'weight',
                    'date', 'lot', 'dum', 'garage', 'frigo', 'client_id', 'driver_id', 'ste_id'
                ]
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les opérations confirmées ne peuvent pas être modifiées. Utilisez 'Annuler' et créez une nouvelle opération."))
        return super(Kal3iyaStockExit, self).write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            # Optimized availability check using read_group
            domain = [
                ('product_id', '=', rec.product_id.id),
                ('lot', '=', rec.lot),
                ('dum', '=', rec.dum),
                ('garage', '=', rec.garage),
                ('frigo', '=', rec.frigo),
                ('state', '=', 'done')
            ]
            res = self.env['kal3iya.stock.move'].read_group(domain, ['qty'], [])
            total_available = res[0]['qty'] if res and res[0]['qty'] else 0.0
            
            if rec.qty > total_available:
                raise UserError(_("Stock insuffisant ! Disponible : %s, Demandé : %s") % (total_available, rec.qty))
            
            # Create Move
            move = self.env['kal3iya.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage,
                'frigo': rec.frigo,
                'qty': -rec.qty,
                'move_type': 'exit',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,

                'weight': rec.weight,
                'calibre': rec.calibre,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'kal3iya.stock.exit',
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
            cancel_move = self.env['kal3iya.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage,
                'frigo': rec.frigo,
                'qty': rec.qty,
                'move_type': 'cancel_exit',
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': rec.name,

                'weight': rec.weight,
                'calibre': rec.calibre,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'res_model': 'kal3iya.stock.exit',
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
