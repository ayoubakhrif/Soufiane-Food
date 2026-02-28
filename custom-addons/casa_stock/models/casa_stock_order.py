from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockOrder(models.Model):
    _name = 'casa.stock.order'
    _description = 'Commande de Stock Casa'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    client_id = fields.Many2one('casa.client', string='Client', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    driver_id = fields.Many2one('casa.driver', string='Chauffeur')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmée'),
        ('cancel', 'Annulée'),
    ], string='État', default='draft', required=True)
    
    order_line_ids = fields.One2many('casa.stock.order.line', 'order_id', string='Lignes de Commande')
    exit_ids = fields.One2many('casa.stock.exit', 'order_id', string='Sorties Générées', readonly=True)

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
            
        return super(CasaStockOrder, self).create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = ['client_id', 'date', 'driver_id', 'order_line_ids']
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Vous ne pouvez pas modifier une commande confirmée."))
        return super(CasaStockOrder, self).write(vals)

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
                }
                new_exit = self.env['casa.stock.exit'].create(exit_vals)
                generated_exits += new_exit
                
            # Now trigger confirmation on all generated exits
            # If any exit fails (e.g. stock insuffisant), Odoo throws a UserError 
            # and automatically rolls back the ENTIRE transaction (no exits or order state changes are saved)
            generated_exits.action_confirm()

            order.write({'state': 'done'})

    def action_cancel(self):
        for order in self:
            if order.state == 'done':
                # Cancel all generated exits
                for exit_record in order.exit_ids:
                    if exit_record.state == 'done':
                        exit_record.action_cancel()
            order.write({'state': 'cancel'})

class CasaStockOrderLine(models.Model):
    _name = 'casa.stock.order.line'
    _description = 'Ligne de Commande Stock Casa'
    
    order_id = fields.Many2one('casa.stock.order', string='Commande', required=True, ondelete='cascade')
    
    product_id = fields.Many2one('casa.product', string='Produit', required=True)
    ste_id = fields.Many2one('casa.ste', string='Société', required=True)
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids unit (Kg)')
    
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
    
    price_sale = fields.Float(string='Prix Vente')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # Find an available stock entry for this product
            stock = self.env['casa.stock.stock'].search([
                ('product_id', '=', self.product_id.id),
                ('quantity', '>', 0)
            ], limit=1, order='id asc') # Older stock first (FIFO suggestion)
            
            if stock:
                self.ste_id = stock.ste_id.id
                self.lot = stock.lot
                self.dum = stock.dum
                self.calibre = stock.calibre
                self.ville = stock.ville
                self.frigo = stock.frigo
                self.weight = stock.weight

    @api.constrains('qty')
    def _check_qty_positive(self):
        for line in self:
            if line.qty <= 0:
                raise UserError(_("La quantité doit être strictement positive."))
