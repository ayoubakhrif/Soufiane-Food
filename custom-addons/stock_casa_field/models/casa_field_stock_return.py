from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockReturn(models.Model):
    _name = 'casa_field.stock.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Retour Client Casa'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    exit_id = fields.Many2one('casa_field.stock.exit', string='Sortie Originale', required=True)
    product_id = fields.Many2one('casa_field.stock.product', related='exit_id.product_id', store=True, string='Produit')
    client_id = fields.Many2one('casa_field.stock.client', related='exit_id.client_id', store=True, string='Client')
    driver_id = fields.Many2one('casa_field.stock.driver', related='exit_id.driver_id', store=True, string='Chauffeur')
    garage = fields.Selection(related='exit_id.garage', store=True, string='Garage')
    frigo = fields.Selection(related='exit_id.frigo', store=True, string='Frigo')
    lot = fields.Char(related='exit_id.lot', store=True, string='Lot')
    dum = fields.Char(related='exit_id.dum', store=True, string='DUM')
    
    qty = fields.Float(string='Quantité Retournée', required=True)
    weight = fields.Float(string='Poids Retourné (Kg)')
    date = fields.Date(string='Date de Retour', required=True, default=fields.Date.context_today)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)

    move_id = fields.Many2one('casa_field.stock.move', string='Mouvement Stock', readonly=True)
    cancel_move_id = fields.Many2one('casa_field.stock.move', string='Mouvement d\'Annulation', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa_field.stock.return') or '/'
        return super(CasaStockReturn, self).create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = ['qty', 'weight', 'date', 'exit_id']
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les retours confirmés ne peuvent pas être modifiés. Utilisez 'Annuler' et créez une nouvelle opération."))
        return super(CasaStockReturn, self).write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.qty > rec.exit_id.qty - rec.exit_id.returned_qty:
                raise UserError(_("La quantité retournée ne peut pas dépasser la quantité restante de la sortie."))
            
            # Create Move
            move = self.env['casa_field.stock.move'].create({
                'product_id': rec.product_id.id,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage,
                'frigo': rec.frigo,
                'qty': rec.qty,
                'weight': rec.weight,
                'move_type': 'return',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'res_model': 'casa_field.stock.return',
                'res_id': rec.id,
            })
            rec.write({
                'state': 'done',
                'move_id': move.id
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Vous ne pouvez annuler que des retours confirmés."))
            
            # Create Reversal Move
            cancel_move = self.env['casa_field.stock.move'].create({
                'product_id': rec.product_id.id,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage,
                'frigo': rec.frigo,
                'qty': -rec.qty,
                'weight': -rec.weight,
                'move_type': 'cancel_return',
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': rec.name,
                'res_model': 'casa_field.stock.return',
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
                raise UserError(_("La quantité retournée doit être strictement positive."))

