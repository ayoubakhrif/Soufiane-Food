from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class CasaStockExit(models.Model):
    _name = 'casa.stock.exit'
    _description = 'Sortie Stock Casa'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    product_id = fields.Many2one('casa.product', string='Produit', required=True)
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids unit (Kg)')
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    is_from_stock = fields.Boolean(string='Depuis Stock', default=False)
    
    price_sale = fields.Float(string='Prix Vente')
    price_purchase = fields.Float(
        string='Prix Achat',
        compute='_compute_price_purchase',
        store=True
    )
    mt_achat = fields.Float(
        string='Montant Achat',
        compute='_compute_amounts',
        store=True
    )
    
    date = fields.Date(string='Date', required=True)
    lot = fields.Char(string='Lot', required=True)
    dum = fields.Char(string='DUM', required=True)
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
    mt_vente = fields.Float(
        string='Montant Vente',
        compute='_compute_amounts',
        store=True
    )

    # Discount traceability fields (written by casa.stock.discount on confirmation)
    discount_amount = fields.Float(string='Réduction', default=0.0)
    validation_user_id = fields.Many2one('res.users', string='Validé par', readonly=True, tracking=True)
    price_sale_final = fields.Float(
        string='Prix Vente Final',
        compute='_compute_final_price', store=True,
    )
    mt_vente_final = fields.Float(
        string='Montant Vente Final',
        compute='_compute_final_price', store=True,
    )

    @api.depends('mt_vente', 'discount_amount', 'tonnage', 'price_sale')
    def _compute_final_price(self):
        for rec in self:
            rec.mt_vente_final = (rec.mt_vente or 0.0) - (rec.discount_amount or 0.0)
            if rec.tonnage:
                rec.price_sale_final = rec.mt_vente_final / rec.tonnage
            else:
                rec.price_sale_final = rec.price_sale or 0.0
    returned_qty = fields.Float(
        string='Qté Retournée',
        compute='_compute_returned_qty'
    )
    margin = fields.Float(
        string='Résultat (Gain / Perte)',
        compute='_compute_amounts',
        store=True
    )
    not_delivered = fields.Boolean(string='Non Livré', default=False, tracking=True)

    move_id = fields.Many2one('casa.stock.move', string='Mouvement Stock', readonly=True)
    cancel_move_id = fields.Many2one('casa.stock.move', string='Mouvement d\'Annulation', readonly=True)
    order_id = fields.Many2one('casa.stock.order', string='Origine (Commande)', readonly=True, ondelete='set null')

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * rec.weight

    @api.depends('tonnage', 'price_purchase', 'price_sale')
    def _compute_amounts(self):
        for rec in self:
            mt_achat = (rec.price_purchase or 0.0) * (rec.tonnage or 0.0)
            mt_vente = (rec.price_sale or 0.0) * (rec.tonnage or 0.0)
            rec.mt_achat = mt_achat
            rec.mt_vente = mt_vente
            rec.margin = mt_vente - mt_achat

    @api.depends('product_id', 'lot', 'dum', 'ville', 'frigo', 'ste_id', 'weight', 'calibre')
    def _compute_price_purchase(self):
        Stock = self.env['casa.stock.stock']
        for rec in self:
            price = rec.price_purchase
            if rec.product_id:
                domain = [
                    ('product_id', '=', rec.product_id.id),
                    ('lot', '=', rec.lot),
                    ('dum', '=', rec.dum),
                    ('ville', '=', rec.ville),
                    ('frigo', '=', rec.frigo),
                    ('ste_id', '=', rec.ste_id.id),
                ]
                
                if rec.weight:
                    domain.append(('weight', '=', rec.weight))
                else:
                    domain.append(('weight', '=', False))
                if rec.calibre:
                    domain.append(('calibre', '=', rec.calibre))
                else:
                    domain.append(('calibre', '=', False))

                stock_records = Stock.search(domain)
                
                if stock_records:
                    if rec.price_purchase and rec.price_purchase in stock_records.mapped('price'):
                        price = rec.price_purchase
                    else:
                        price = stock_records[0].price
                else:
                    price = 0.0
            rec.price_purchase = price


    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa.stock.exit') or '/'
        return super().create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = [
                    'product_id', 'qty', 'weight', 'price_sale',
                    'date', 'lot', 'dum', 'ville', 'frigo', 'client_id', 'driver_id', 'ste_id'
                ]
                # 'not_delivered' is EXPLICITLY ALLOWED to be changed
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les opérations confirmées ne peuvent pas être modifiées. Utilisez 'Annuler' et créez une nouvelle opération."))
        return super().write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            # Optimized availability check using helper
            total_available = self.env['casa.stock.entry']._get_current_stock_qty(rec, price=rec.price_purchase)
            
            if rec.qty > total_available:
                raise UserError(_(
                    "Stock insuffisant pour le prix %s MAD ! Disponible : %s, Demandé : %s"
                ) % (rec.price_purchase, total_available, rec.qty))
            
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
                'price_purchase': rec.price_purchase,
            })
            rec.write({
                'state': 'done',
                'move_id': move.id,
                'validation_user_id': self.env.user.id
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
                'ste_id': rec.ste_id.id,
                'res_model': 'casa.stock.exit',
                'res_id': rec.id,
                'price_purchase': rec.price_purchase,
            })
            rec.write({
                'state': 'cancel',
                'cancel_move_id': cancel_move.id
            })

    def _compute_returned_qty(self):
        for rec in self:
            returns = self.env['casa.stock.return'].search([
                ('exit_id', '=', rec.id),
                ('state', '=', 'done')
            ])
            rec.returned_qty = sum(returns.mapped('qty'))

    def action_new_return(self):
        self.ensure_one()
        return {
            'name': _('Retour Client'),
            'type': 'ir.actions.act_window',
            'res_model': 'casa.stock.return',
            'view_mode': 'form',
            'context': {
                'default_exit_id': self.id,
                'default_product_id': self.product_id.id,
                'default_client_id': self.client_id.id,
                'default_ste_id': self.ste_id.id,
                'default_driver_id': self.driver_id.id,
                'default_lot': self.lot,
                'default_dum': self.dum,
                'default_frigo': self.frigo,
                'default_calibre': self.calibre,
            }
        }

    @api.constrains('qty')
    def _check_qty_positive(self):
        for rec in self:
            if rec.qty <= 0:
                raise UserError(_("La quantité doit être strictement positive."))

    @api.constrains('qty', 'product_id', 'lot', 'dum', 'ville', 'frigo', 'ste_id', 'weight', 'calibre', 'price_purchase')
    def _check_stock_availability(self):
        for rec in self:
            if rec.state != 'draft':
                continue
                
            total_available = self.env['casa.stock.entry']._get_current_stock_qty(rec, price=rec.price_purchase)
            
            if rec.qty > total_available:
                raise UserError(_(
                    "Quantité insuffisante pour l'article %(product)s au prix %(price)s MAD.\n"
                    "Demandée: %(req)s, Disponible: %(avail)s",
                    product=rec.product_id.name,
                    price=rec.price_purchase,
                    req=rec.qty,
                    avail=total_available
                ))
