from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockOrder(models.Model):
    _name = 'casa.stock.order'
    _description = 'Commande de Stock Casa'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', readonly=True, default='/')
    client_id = fields.Many2one('casa.client', string='Client', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    driver_id = fields.Many2one('casa.driver', string='Chauffeur', tracking=True)
    
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', required=True, default='casa', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('done', 'Validée'),
        ('cancel', 'Annulée'),
    ], string='État', default='draft', required=True, tracking=True)
    
    order_line_ids = fields.One2many('casa.stock.order.line', 'order_id', string='Lignes de Commande')
    exit_ids = fields.One2many('casa.stock.exit', 'order_id', string='Sorties Générées', readonly=True)
    is_cancel_hidden = fields.Boolean(compute='_compute_is_cancel_hidden')

    def _compute_is_cancel_hidden(self):
        is_manager = self.env.user.has_group('casa_stock.group_manager')
        hidden = not is_manager
        for rec in self:
            rec.is_cancel_hidden = hidden

    @api.model
    def create(self, vals):
        # We will set the sequence when confirming the order or on creation if we have the date
        if vals.get('name', '/') == '/':
            order_date = vals.get('date') or fields.Date.context_today(self).strftime('%Y-%m-%d')
            # Extract Day and Month
            date_obj = fields.Date.from_string(order_date)
            dd_mm = date_obj.strftime('%d/%m')
            
            # Find the highest sequence for this day
            domain = [
                ('name', 'like', f'Commande {dd_mm} %')
            ]
            last_order = self.search(domain, order='name desc', limit=1)
            
            if last_order and last_order.name:
                try:
                    last_seq = int(last_order.name.split(' ')[-1])
                    new_seq = last_seq + 1
                except ValueError:
                    new_seq = 1
            else:
                new_seq = 1
                
            vals['name'] = f'Commande {dd_mm} {new_seq:02d}'
            
        return super().create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = ['client_id', 'date', 'driver_id', 'order_line_ids']
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Vous ne pouvez pas modifier une commande validée."))
            
            elif rec.state == 'confirmed':
                # Allow order_line_ids if we're only updating price_sale on existing lines
                # But block other header fields
                header_forbidden = ['client_id', 'date', 'driver_id']
                if any(f in vals for f in header_forbidden):
                    raise UserError(_("Vous ne pouvez pas modifier le client, la date ou le chauffeur d'une commande confirmée."))
                
                # Check order_line_ids commands
                if 'order_line_ids' in vals:
                    for command in vals['order_line_ids']:
                        # command is (code, id, vals)
                        if command[0] == 0: # Create
                            raise UserError(_("Vous ne pouvez pas ajouter de nouvelles lignes à une commande confirmée."))
                        if command[0] == 2: # Delete
                            raise UserError(_("Vous ne pouvez pas supprimer de lignes d'une commande confirmée."))
                        if command[0] == 1: # Update
                            line_vals = command[2]
                            if any(f != 'price_sale' for f in line_vals):
                                raise UserError(_("Seul le prix de vente peut être modifié sur une commande confirmée."))
        return super().write(vals)

    def action_confirm(self):
        for order in self:
            if order.state != 'draft':
                continue
                
            if not order.order_line_ids:
                raise UserError(_("Vous devez ajouter au moins une ligne de commande avant de confirmer."))
            
            # Loop through lines to generate exits
            generated_exits = self.env['casa.stock.exit']
            
            for line in order.order_line_ids:
                exit_vals = {
                    'order_id': order.id,
                    'order_line_id': line.id,
                    'client_id': order.client_id.id,
                    'driver_id': order.driver_id.id,
                    'ste_id': line.ste_id.id,
                    'date': order.date,
                    'product_id': line.product_id.id,
                    'qty': line.qty,
                    'weight': line.weight,
                    'price_sale': line.price_sale,
                    'lot': line.lot,
                    'dum': line.dum,
                    'calibre': line.calibre,
                    'ville': line.ville,
                    'frigo': line.frigo,
                    'price_purchase': line.stock_id.price,
                }
                new_exit = self.env['casa.stock.exit'].create(exit_vals)
                generated_exits += new_exit
                
            # Now trigger confirmation on all generated exits
            # If any exit fails (e.g. stock insuffisant), Odoo throws a UserError 
            # and automatically rolls back the ENTIRE transaction (no exits or order state changes are saved)
            generated_exits.action_confirm()

            order.write({'state': 'confirmed'})

    def action_validate(self):
        for order in self:
            if order.state != 'confirmed':
                continue
            
            # Validate generated exits
            order.exit_ids.action_validate()
            order.write({'state': 'done'})

    def action_cancel(self):
        for order in self:
            if order.state in ('confirmed', 'done'):
                # Cancel all generated exits
                for exit_record in order.exit_ids:
                    if exit_record.state in ('confirmed', 'done'):
                        exit_record.action_cancel()
            order.write({'state': 'cancel'})

    def action_draft_with_exits(self):
        for order in self:
            if order.state not in ('confirmed', 'done'):
                continue

            # Step 1: Cancel confirmed/done exits to restore stock via reversal moves
            for exit_record in order.exit_ids:
                if exit_record.state in ('confirmed', 'done'):
                    exit_record.action_cancel()

            # Step 2: Delete ALL exits linked to this order (including draft and cancelled)
            # This prevents duplicates when re-confirming creates fresh exits from order lines
            # We use sudo() because we want to allow managers to reset orders without giving them general unlink access on exits
            order.exit_ids.sudo().unlink()

            # Step 3: Set order back to draft so lines can be edited/added
            order.write({'state': 'draft'})

class CasaStockOrderLine(models.Model):
    _name = 'casa.stock.order.line'
    _description = 'Ligne de Commande Stock Casa'
    
    order_id = fields.Many2one('casa.stock.order', string='Commande', required=True, ondelete='cascade')
    
    stock_id = fields.Many2one('casa.stock.stock', string='Stock', required=True)
    product_id = fields.Many2one('casa.product', string='Produit', related='stock_id.product_id', store=True)
    ste_id = fields.Many2one('casa.ste', string='Société')
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(
        string='Poids unit (Kg)',
        related='stock_id.weight',
        store=True,
        readonly=False
    )
    
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    calibre = fields.Char(string='Calibre')
    
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville')
    
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo')
    
    price_sale = fields.Float(string='Prix Vente', required=True)
    poids = fields.Char(string='Poids', compute='_compute_poids')

    @api.depends('weight')
    def _compute_poids(self):
        for rec in self:
            rec.poids = f"{rec.weight or 0.0}Kg"

    @api.onchange('stock_id')
    def _onchange_stock_id(self):
        if self.stock_id:
            self.ste_id = self.stock_id.ste_id.id
            self.lot = self.stock_id.lot
            self.dum = self.stock_id.dum
            self.calibre = self.stock_id.calibre
            self.ville = self.stock_id.ville
            self.frigo = self.stock_id.frigo
            self.weight = self.stock_id.weight

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        order_msgs = {}
        for line in lines:
            if line.order_id:
                if line.order_id not in order_msgs:
                    order_msgs[line.order_id] = []
                order_msgs[line.order_id].append(
                    f"<li><span style='color: green;'><b>Ligne ajoutée</b></span>: <b>{line.product_id.name}</b> (Qté: {line.qty})</li>"
                )
        for order, msgs in order_msgs.items():
            order.message_post(body=f"<ul>{''.join(msgs)}</ul>")
        return lines

    def write(self, vals):
        # Deep audit: log line changes to parent order chatter
        tracking_fields = {
            'qty': _('Quantité'),
            'price_sale': _('Prix Vente'),
            'stock_id': _('Stock/Produit'),
        }
        
        for rec in self:
            changes = []
            for field, label in tracking_fields.items():
                if field in vals:
                    old_val = rec[field]
                    new_val = vals[field]
                    if old_val != new_val:
                        # For Many2one, get names
                        if field == 'stock_id':
                            old_name = old_val.display_name if old_val else 'None'
                            new_name = self.env['casa.stock.stock'].browse(new_val).display_name if new_val else 'None'
                            changes.append(f"<li><b>{label}</b>: {old_name} &rarr; {new_name}</li>")
                        else:
                            changes.append(f"<li><b>{label}</b>: {old_val} &rarr; {new_val}</li>")
            
            if changes and rec.order_id:
                # Get a fresh name in case it changed in this transaction
                prod_name = rec.product_id.name
                msg = f"<b>Ligne modifiée ({prod_name}):</b><ul>{''.join(changes)}</ul>"
                rec.order_id.message_post(body=msg)
                
        return super().write(vals)

    def unlink(self):
        order_msgs = {}
        for rec in self:
            if rec.order_id:
                if rec.order_id not in order_msgs:
                    order_msgs[rec.order_id] = []
                order_msgs[rec.order_id].append(
                    f"<li><span style='color: red;'><b>Ligne supprimée</b></span>: <b>{rec.product_id.name}</b> (Qté: {rec.qty})</li>"
                )
        for order, msgs in order_msgs.items():
            order.message_post(body=f"<ul>{''.join(msgs)}</ul>")
        return super().unlink()

    @api.constrains('qty')
    def _check_qty_positive(self):
        for line in self:
            if line.qty <= 0:
                raise UserError(_("La quantité doit être strictement positive."))
                
    @api.constrains('qty', 'stock_id')
    def _check_stock_availability(self):
        for line in self:
            if line.stock_id and line.qty > line.stock_id.quantity:
                raise UserError(_(
                    "Quantité insuffisante pour l'article %(product)s.\n"
                    "Demandée: %(req)s, Disponible: %(avail)s",
                    product=line.product_id.name,
                    req=line.qty,
                    avail=line.stock_id.quantity
                ))
