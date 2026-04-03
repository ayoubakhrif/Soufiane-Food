from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockPerte(models.Model):
    _name = 'casa.stock.perte'
    _description = 'Pertes de Stock Casa'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='/')
    stock_id = fields.Many2one('casa.stock.stock', string='Article Stock', required=True, states={'draft': [('readonly', False)]})
    
    product_id = fields.Many2one('casa.product', string='Produit', tracking=True)
    lot = fields.Char(string='Lot', tracking=True)
    dum = fields.Char(string='DUM', tracking=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', tracking=True)
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo', tracking=True)
    ste_id = fields.Many2one('casa.ste', string='Société', tracking=True)
    weight = fields.Float(string='Poids (Kg)', tracking=True)
    calibre = fields.Char(string='Calibre', tracking=True)
    price_purchase = fields.Float(string='Prix Achat', tracking=True)
    stock_soufiane = fields.Boolean(string='Stock Soufiane', default=False, tracking=True)

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    qty = fields.Float(string='Quantité Perdue', required=True, tracking=True)
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    commentary = fields.Text(string='Commentaire', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Validé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    create_uid = fields.Many2one('res.users', string='Créé par', readonly=True)
    validation_user_id = fields.Many2one('res.users', string='Validé par', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('casa.stock.perte') or '/'
        return super(CasaStockPerte, self).create(vals_list)

    @api.onchange('stock_id')
    def _onchange_stock_id(self):
        if self.stock_id:
            self.product_id = self.stock_id.product_id
            self.lot = self.stock_id.lot
            self.dum = self.stock_id.dum
            self.ville = self.stock_id.ville
            self.frigo = self.stock_id.frigo
            self.ste_id = self.stock_id.ste_id
            self.weight = self.stock_id.weight
            self.calibre = self.stock_id.calibre
            self.price_purchase = self.stock_id.price
            self.stock_soufiane = self.stock_id.stock_soufiane

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = (rec.qty * rec.weight) / 1000.0 if rec.weight else 0.0

    def action_validate(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Seules les déclarations de pertes en brouillon peuvent être validées."))
            if rec.qty <= 0:
                raise UserError(_("La quantité perdue doit être strictement positive."))

            # Créer le mouvement de stock (Ajustement négatif)
            move_vals = {
                'move_type': 'perte',
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'qty': -rec.qty,
                'date': rec.date,
                'reference': rec.name,
                'user_id': self.env.user.id,
                'res_model': self._name,
                'res_id': rec.id,
                'price_purchase': rec.price_purchase,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'ste_id': rec.ste_id.id,
                'stock_soufiane': rec.stock_soufiane,
            }
            self.env['casa.stock.move'].create(move_vals)
            
            rec.write({
                'state': 'done',
                'validation_user_id': self.env.user.id
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Vous ne pouvez annuler qu'une perte validée."))
            
            # Find and reverse the move
            moves = self.env['casa.stock.move'].search([('res_model', '=', self._name), ('res_id', '=', rec.id)])
            for move in moves:
                move.copy({
                    'qty': -move.qty,
                    'reference': f'Annulation: {rec.name}',
                    'move_type': 'adjustment',
                })
            
            rec.write({'state': 'cancel'})
