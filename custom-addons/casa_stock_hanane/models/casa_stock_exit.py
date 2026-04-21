from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class CasaStockExit(models.Model):
    _name = 'casa_hanane.stock.exit'
    _description = 'Sortie Stock Casa (Hanane)'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', readonly=True, default='/')
    product_id = fields.Many2one('casa_hanane.product', string='Produit', required=True, tracking=True)
    qty = fields.Float(string='Quantité', required=True, tracking=True)
    weight = fields.Float(string='Poids unit (Kg)', tracking=True)
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    is_from_stock = fields.Boolean(string='Depuis Stock', default=False)
    
    stock_id = fields.Many2one('casa_hanane.stock.stock', string='Changer d\'Article Stock')
    
    price_sale = fields.Float(string='Prix Vente', tracking=True)
    price_sale_corrected = fields.Float(string='Nouveau Prix de Vente', tracking=True)
    price_purchase = fields.Float(
        string='Prix Achat',
        compute='_compute_price_purchase',
        store=True,
        readonly=False,
        tracking=True
    )
    mt_achat = fields.Float(
        string='Montant Achat',
        compute='_compute_amounts',
        store=True
    )
    
    date = fields.Date(string='Date', required=True, tracking=True)
    lot = fields.Char(string='Lot', tracking=True)
    dum = fields.Char(string='DUM', tracking=True)
    calibre = fields.Char(string='Calibre', tracking=True)
    stock_soufiane = fields.Boolean(string='Stock Soufiane', default=False, tracking=True)
    
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', required=True, tracking=True)
    
    
    client_id = fields.Many2one('casa_hanane.client', string='Client', tracking=True)
    driver_id = fields.Many2one('casa_hanane.driver', string='Chauffeur', tracking=True)
    ste_id = fields.Many2one('casa_hanane.ste', string='Société', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Validé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)
    
    mt_vente = fields.Float(
        string='Montant Vente',
        compute='_compute_amounts',
        store=True
    )
    
    # Discount traceability fields (written by casa_hanane.stock.discount on confirmation)
    discount_amount = fields.Float(string='Réduction', default=0.0, tracking=True)
    validation_user_id = fields.Many2one('res.users', string='Validé par', readonly=True, tracking=True)
    poids = fields.Char(string='Poids', compute='_compute_poids')
    week = fields.Char(string='Semaine', compute='_compute_week', store=True)

    @api.depends('date')
    def _compute_week(self):
        for record in self:
            if record.date:
                record.week = record.date.strftime("%Y-W%W")
            else:
                record.week = False

    @api.depends('weight')
    def _compute_poids(self):
        for rec in self:
            rec.poids = f"{rec.weight or 0.0}Kg"

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
    not_delivered = fields.Boolean(string='Pointé', default=False, tracking=True)

    move_id = fields.Many2one('casa_hanane.stock.move', string='Mouvement Stock', readonly=True)
    cancel_move_id = fields.Many2one('casa_hanane.stock.move', string='Mouvement d\'Annulation', readonly=True)
    order_id = fields.Many2one('casa_hanane.stock.order', string='Origine (Commande)', readonly=True, ondelete='set null')
    order_line_id = fields.Many2one('casa_hanane.stock.order.line', string='Ligne de Commande', readonly=True, ondelete='set null')
    is_cancel_hidden = fields.Boolean(compute='_compute_is_cancel_hidden')

    @api.onchange('stock_id')
    def _onchange_stock_id(self):
        if self.stock_id:
            self.product_id = self.stock_id.product_id.id
            self.lot = self.stock_id.lot
            self.dum = self.stock_id.dum
            self.calibre = self.stock_id.calibre
            self.ville = self.stock_id.ville
            self.ste_id = self.stock_id.ste_id.id
            self.weight = self.stock_id.weight
            self.price_purchase = self.stock_id.price
            self.stock_soufiane = self.stock_id.stock_soufiane
            # Clear it so it doesn't linger visually if not needed, or keep it.
            # We keep it so user can see what they selected before saving.

    def _compute_is_cancel_hidden(self):
        is_manager = self.env.user.has_group('casa_stock_hanane.group_manager')
        hidden = not is_manager
        for rec in self:
            rec.is_cancel_hidden = hidden

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

    @api.depends('product_id', 'lot', 'dum', 'ville', 'ste_id', 'weight', 'calibre')
    def _compute_price_purchase(self):
        Stock = self.env['casa_hanane.stock.stock']
        for rec in self:
            price = rec.price_purchase
            if rec.product_id:
                domain = [
                    ('product_id', '=', rec.product_id.id),
                    ('ville', '=', rec.ville),
                    ('ste_id', '=', rec.ste_id.id),
                ]
                
                domain.append(('weight', '=', rec.weight or 0.0))
                
                if rec.lot:
                    domain.append(('lot', '=', rec.lot))
                else:
                    domain.append(('lot', 'in', [False, '']))
                    
                if rec.dum:
                    domain.append(('dum', '=', rec.dum))
                else:
                    domain.append(('dum', 'in', [False, '']))
                    
                if rec.calibre:
                    domain.append(('calibre', '=', rec.calibre))
                else:
                    domain.append(('calibre', 'in', [False, '']))

                stock_records = Stock.search(domain, order='quantity desc')
                
                if stock_records:
                # Keep current price if it's valid for this stock group
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
            vals['name'] = self.env['ir.sequence'].next_by_code('casa_hanane.stock.exit') or '/'
        return super().create(vals)

    def write(self, vals):
        # 1. Security check: prevent modification of sensitive fields
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = [
                    'product_id', 'qty', 'weight', 'price_sale',
                    'date', 'lot', 'dum', 'ville', 'client_id', 'driver_id', 'ste_id'
                ]
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les opérations validées ne peuvent pas être modifiées."))
            
            elif rec.state == 'confirmed':
                # Allow price_sale, but block everything else
                forbidden_fields = [
                    'product_id', 'qty', 'weight',
                    'date', 'lot', 'dum', 'ville', 'client_id', 'driver_id', 'ste_id'
                ]
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Seul le prix de vente peut être modifié sur une sortie confirmée. Pour le reste, utilisez 'Remettre en brouillon'."))
        
        # 2. Perform the write
        res = super().write(vals)
        
        # 3. If price_sale changed on a confirmed exit, sync to the move ledger
        if 'price_sale' in vals:
            for rec in self:
                if rec.state == 'confirmed' and rec.move_id:
                    rec.move_id.write({'price_sale': vals['price_sale']})

        # 4. Sync changes back to Commande
        sync_fields = ['product_id', 'qty', 'price_sale', 'weight', 'lot', 'dum', 'calibre', 'ville', 'ste_id']
        if any(f in vals for f in sync_fields):
            for rec in self:
                if rec.order_line_id:
                    # Sensitive fields still only sync in draft
                    # But price_sale can now sync in confirmed state too
                    if rec.state == 'draft':
                        line_vals = {f: vals[f] for f in sync_fields if f in vals}
                        if line_vals:
                            rec.order_line_id.write(line_vals)
                    elif rec.state == 'confirmed' and 'price_sale' in vals:
                        rec.order_line_id.write({'price_sale': vals['price_sale']})
        return res

    @api.constrains('price_sale_corrected', 'price_sale')
    def _check_sale_prices(self):
        for rec in self:
            if rec.price_sale <= 0:
                raise UserError(_("Le prix de vente de %s doit être strictement positif.") % rec.product_id.name)
            if rec.price_sale_corrected > 0:
                if rec.price_sale_corrected > rec.price_sale:
                    raise UserError(_(
                        "Le nouveau prix de vente (%s) pour le produit %s ne peut pas être supérieur au prix initial (%s)."
                    ) % (rec.price_sale_corrected, rec.product_id.name, rec.price_sale))
            elif 'price_sale_corrected' in self.env.context: # If being set
                 if rec.price_sale_corrected < 0:
                     raise UserError(_("Le nouveau prix de vente doit être positif."))

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            # Optimized availability check using helper
            total_available = self.env['casa_hanane.stock.entry']._get_current_stock_qty(rec, price=rec.price_purchase)
            
            if rec.qty > total_available:
                raise UserError(_(
                    "Stock insuffisant pour le prix %s MAD ! Disponible : %s, Demandé : %s"
                ) % (rec.price_purchase, total_available, rec.qty))
            
            # Create Move
            move = self.env['casa_hanane.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'qty': -rec.qty,
                'move_type': 'exit',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'price_sale': rec.price_sale,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'stock_soufiane': rec.stock_soufiane,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'casa_hanane.stock.exit',
                'res_id': rec.id,
                'price_purchase': rec.price_purchase,
            })
            rec.write({
                'state': 'confirmed',
                'move_id': move.id,
            })

    def action_validate(self):
        orders_to_check = self.env['casa_hanane.stock.order']
        for rec in self:
            if rec.state != 'confirmed':
                continue
            rec.write({
                'state': 'done',
                'validation_user_id': self.env.user.id
            })
            if rec.order_id:
                orders_to_check |= rec.order_id
        
        # Auto-validate parent orders if all their exits are now 'done'
        for order in orders_to_check:
            if order.state == 'confirmed' and all(ex.state == 'done' for ex in order.exit_ids):
                order.write({'state': 'done'})

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('confirmed', 'done'):
                raise UserError(_("Vous ne pouvez annuler que des sorties confirmées ou validées."))
            
            # Create Reversal Move
            cancel_move = self.env['casa_hanane.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'qty': rec.qty,
                'move_type': 'cancel_exit',
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': rec.name,
                'price_sale': rec.price_sale,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'stock_soufiane': rec.stock_soufiane,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'casa_hanane.stock.exit',
                'res_id': rec.id,
                'price_purchase': rec.price_purchase,
            })
            rec.write({
                'state': 'cancel',
                'cancel_move_id': cancel_move.id
            })

    def action_draft(self):
        for rec in self:
            if rec.state not in ('confirmed', 'done', 'cancel'):
                raise UserError(_("Seules les opérations confirmées, validées ou annulées peuvent être remises en brouillon."))
                
            if rec.state in ('confirmed', 'done'):
                # Create Reversal Move
                cancel_move = self.env['casa_hanane.stock.move'].create({
                    'product_id': rec.product_id.id,
                    'lot': rec.lot,
                    'dum': rec.dum,
                    'ville': rec.ville,
                    'qty': rec.qty,
                    'move_type': 'cancel_exit',
                    'state': 'done',
                    'date': fields.Datetime.now(),
                    'reference': rec.name + ' (Remise Brouillon)',
                    'price_sale': rec.price_sale,
                    'weight': rec.weight,
                    'calibre': rec.calibre,
                    'stock_soufiane': rec.stock_soufiane,
                    'client_id': rec.client_id.id,
                    'driver_id': rec.driver_id.id,
                    'ste_id': rec.ste_id.id,
                    'res_model': 'casa_hanane.stock.exit',
                    'res_id': rec.id,
                    'price_purchase': rec.price_purchase,
                })
                rec.write({
                    'state': 'draft',
                    'cancel_move_id': cancel_move.id,
                    'move_id': False,
                    'validation_user_id': False
                })
            else:
                rec.write({
                    'state': 'draft',
                    'move_id': False,
                    'cancel_move_id': False,
                    'validation_user_id': False
                })

    def _compute_returned_qty(self):
        for rec in self:
            returns = self.env['casa_hanane.stock.return'].search([
                ('exit_id', '=', rec.id),
                ('state', '=', 'done')
            ])
            rec.returned_qty = sum(returns.mapped('qty'))

    def action_new_return(self):
        self.ensure_one()
        return {
            'name': _('Retour Client'),
            'type': 'ir.actions.act_window',
            'res_model': 'casa_hanane.stock.return',
            'view_mode': 'form',
            'context': {
                'default_exit_id': self.id,
                'default_product_id': self.product_id.id,
                'default_client_id': self.client_id.id,
                'default_ste_id': self.ste_id.id,
                'default_driver_id': self.driver_id.id,
                'default_lot': self.lot,
                'default_dum': self.dum,
                'default_calibre': self.calibre,
            }
        }

    @api.constrains('qty')
    def _check_qty_positive(self):
        for rec in self:
            if rec.qty <= 0:
                raise UserError(_("La quantité doit être strictement positive."))

    @api.constrains('qty', 'product_id', 'lot', 'dum', 'ville', 'ste_id', 'weight', 'calibre', 'price_purchase')
    def _check_stock_availability(self):
        for rec in self:
            if rec.state != 'draft':
                continue
                
            total_available = self.env['casa_hanane.stock.entry']._get_current_stock_qty(rec, price=rec.price_purchase)
            
            if rec.qty > total_available:
                # Audit: Where is the rest of the stock?
                all_stock_found = []
                # Search across all ste_ids for this product/lot/weight
                domain_audit = [
                    ('product_id', '=', rec.product_id.id),
                    ('state', '=', 'done'),
                    ('weight', '>=', (rec.weight or 0.0) - 0.01),
                    ('weight', '<=', (rec.weight or 0.0) + 0.01),
                ]
                if rec.lot: domain_audit.append(('lot', '=', rec.lot))
                if rec.dum: domain_audit.append(('dum', '=', rec.dum))
                
                moves = self.env['casa_hanane.stock.move'].read_group(domain_audit, ['qty', 'ste_id', 'ville'], ['ste_id', 'ville'], lazy=False)
                for move in moves:
                    if move['qty'] > 0:
                        ville_name = dict(self._fields['ville'].selection).get(move['ville'], move['ville'])
                        ste_name = self.env['casa_hanane.ste'].browse(move['ste_id'][0]).name if move['ste_id'] else 'Aucune'
                        all_stock_found.append(f"- {move['qty']} unités à {ville_name} (Sté: {ste_name})")

                audit_msg = "\n".join(all_stock_found) if all_stock_found else "Aucun stock trouvé avec ces caractéristiques (Lot, DUM, Poids)."
                
                total_any_price = self.env['casa_hanane.stock.entry']._get_current_stock_qty(rec, price=None)
                raise UserError(_(
                    "Stock insuffisant pour l'article %(product)s !\n\n"
                    "Vérifiez que la Ville et Société correspondent bien à votre besoin."
                ) % {
                    'product': rec.product_id.name,
                    'price': rec.price_purchase,
                    'avail': total_available,
                    'req': rec.qty,
                    'total': total_any_price,
                    'audit': audit_msg,
                    'ville': dict(self._fields['ville'].selection).get(rec.ville, rec.ville),
                    'ste': rec.ste_id.name or 'Aucune'
                })
