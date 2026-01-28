from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockReturn(models.Model):
    _name = 'casa.stock.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Retour Client Stock Casa'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    
    exit_id = fields.Many2one('casa.stock.exit', string='Sortie d\'origine', required=True, readonly=True)
    
    # Inherited fields from Exit
    product_id = fields.Many2one( related='exit_id.product_id', store=True, string='Produit')
    lot = fields.Char(related='exit_id.lot', store=True, string='Lot')
    dum = fields.Char(related='exit_id.dum', store=True, string='DUM')
    ville = fields.Selection(related='exit_id.ville', store=True, string='Ville')
    frigo = fields.Selection(related='exit_id.frigo', store=True, string='Frigo')
    client_id = fields.Many2one('casa.client', related='exit_id.client_id', store=True, string='Client')
    ste_id = fields.Many2one('casa.ste', related='exit_id.ste_id', store=True, string='Société')
    calibre = fields.Char(related='exit_id.calibre', store=True, string='Calibre')
    
    # User Inputs
    date = fields.Date(string='Date de Retour', default=fields.Date.context_today, required=True)
    driver_id = fields.Many2one('casa.driver', string='Chauffeur')
    qty = fields.Float(string='Quantité Retournée', required=True)
    weight = fields.Float(related='exit_id.weight', string='Poids unit (Kg)', readonly=True)
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    
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
            vals['name'] = self.env['ir.sequence'].next_by_code('casa.stock.return') or '/'
        return super(CasaStockReturn, self).create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = ['exit_id', 'qty', 'date', 'driver_id']
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les retours confirmés ne peuvent pas être modifiés. Utilisez 'Annuler'."))
        return super(CasaStockReturn, self).write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            # Validation
            if rec.qty <= 0:
                raise UserError(_("La quantité retournée doit être strictement positive."))
            
            # Check total returned quantity
            # Note: We don't have return_ids on exit model yet (implied inverse relation field), 
            # so we search manually to be safe or assuming standard O2M name 'return_ids' won't work unless defined on exit.
            # Let's search manually.
            already_returned = sum(self.search([
                ('exit_id', '=', rec.exit_id.id),
                ('state', '=', 'done'),
                ('id', '!=', rec.id)
            ]).mapped('qty'))
            
            if (already_returned + rec.qty) > rec.exit_id.qty:
                raise UserError(_("La quantité totale retournée (%s) ne peut pas dépasser la quantité de la sortie initiale (%s).") % (already_returned + rec.qty, rec.exit_id.qty))
            
            # Create Move (Positive quantity for return)
            # 'return' type implies adding back to stock
            move = self.env['casa.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'frigo': rec.frigo,
                'qty': rec.qty,  # Positive quantity adds to stock
                'move_type': 'return',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'casa.stock.return',
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
            
            # Reverse Move (Negative quantity)
            cancel_move = self.env['casa.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'frigo': rec.frigo,
                'qty': -rec.qty,
                'move_type': 'cancel_return', 
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': _('Annulation: ') + rec.name,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'casa.stock.return',
                'res_id': rec.id,
            })
            
            rec.write({
                'state': 'cancel',
                'cancel_move_id': cancel_move.id
            })
