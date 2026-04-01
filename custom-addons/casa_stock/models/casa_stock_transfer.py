from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CasaStockTransfer(models.Model):
    _name = 'casa.stock.transfer'
    _description = 'Transfert de Stock Casa'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', readonly=True, default='/')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    note = fields.Text(string='Notes')

    # Source
    source_stock_id = fields.Many2one('casa.stock.stock', string='Stock Source', required=True, tracking=True)
    product_id = fields.Many2one('casa.product', string='Produit')
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    calibre = fields.Char(string='Calibre')
    weight = fields.Float(string='Poids unit (Kg)')
    price_purchase = fields.Float(string='Prix Achat')
    source_ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville Source')
    source_ste_id = fields.Many2one('casa.ste', string='Société Source')
    available_qty = fields.Float(string='Qté Disponible')

    # Transfer quantity
    qty = fields.Float(string='Quantité à transférer', required=True, tracking=True)

    # Destination
    dest_ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville Destination', required=True, tracking=True)
    dest_ste_id = fields.Many2one('casa.ste', string='Société Destination', tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Effectué'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    # Ledger move tracking
    move_out_id = fields.Many2one('casa.stock.move', string='Mouvement Sortie', readonly=True)
    move_in_id = fields.Many2one('casa.stock.move', string='Mouvement Entrée', readonly=True)
    move_cancel_out_id = fields.Many2one('casa.stock.move', string='Annulation Sortie', readonly=True)
    move_cancel_in_id = fields.Many2one('casa.stock.move', string='Annulation Entrée', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa.stock.transfer') or '/'
        return super().create(vals)

    @api.onchange('source_stock_id')
    def _onchange_source_stock_id(self):
        if self.source_stock_id:
            s = self.source_stock_id
            self.product_id = s.product_id.id
            self.lot = s.lot
            self.dum = s.dum
            self.calibre = s.calibre
            self.weight = s.weight
            self.price_purchase = s.price
            self.source_ville = s.ville
            self.source_ste_id = s.ste_id.id
            self.available_qty = s.quantity
        else:
            self.product_id = False
            self.lot = False
            self.dum = False
            self.calibre = False
            self.weight = 0.0
            self.price_purchase = 0.0
            self.source_ville = False
            self.source_ste_id = False
            self.available_qty = 0.0

    def action_validate(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Seuls les transferts en brouillon peuvent être validés."))

            if rec.qty <= 0:
                raise UserError(_("La quantité doit être strictement positive."))

            # Always read fresh values from source_stock_id to avoid onchange save issues
            src = rec.source_stock_id
            if not src:
                raise UserError(_("Veuillez sélectionner un stock source."))

            product_id = src.product_id.id
            lot = src.lot
            dum = src.dum
            calibre = src.calibre
            weight = src.weight
            price_purchase = src.price
            source_ville = src.ville
            source_ste_id = src.ste_id.id if src.ste_id else False

            # Stock availability check
            if rec.qty > (src.quantity or 0.0):
                raise UserError(_(
                    "Stock insuffisant pour le transfert!\n"
                    "Disponible: %s, Demandé: %s"
                ) % (src.quantity, rec.qty))

            now = fields.Datetime.now()
            ref = rec.name

            # EXIT move from source
            move_out = self.env['casa.stock.move'].create({
                'product_id': product_id,
                'lot': lot,
                'dum': dum,
                'ville': source_ville,
                'ste_id': source_ste_id,
                'qty': -rec.qty,
                'weight': weight,
                'calibre': calibre,
                'price_purchase': price_purchase,
                'move_type': 'exit',
                'state': 'done',
                'date': now,
                'reference': ref + ' (Sortie)',
                'res_model': 'casa.stock.transfer',
                'res_id': rec.id,
            })

            # ENTRY move to destination
            move_in = self.env['casa.stock.move'].create({
                'product_id': product_id,
                'lot': lot,
                'dum': dum,
                'ville': rec.dest_ville,
                'ste_id': rec.dest_ste_id.id if rec.dest_ste_id else False,
                'qty': rec.qty,
                'weight': weight,
                'calibre': calibre,
                'price_purchase': price_purchase,
                'move_type': 'entry',
                'state': 'done',
                'date': now,
                'reference': ref + ' (Entrée)',
                'res_model': 'casa.stock.transfer',
                'res_id': rec.id,
            })

            rec.write({
                'state': 'done',
                'move_out_id': move_out.id,
                'move_in_id': move_in.id,
                # Also persist source details for use in cancellation
                'product_id': product_id,
                'lot': lot,
                'dum': dum,
                'calibre': calibre,
                'weight': weight,
                'price_purchase': price_purchase,
                'source_ville': source_ville,
                'source_ste_id': source_ste_id,
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Seuls les transferts effectués peuvent être annulés."))

            now = fields.Datetime.now()
            ref = rec.name

            # Reversal: re-add to source
            move_cancel_out = self.env['casa.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.source_ville,
                'ste_id': rec.source_ste_id.id,
                'qty': rec.qty,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'price_purchase': rec.price_purchase,
                'move_type': 'cancel_exit',
                'state': 'done',
                'date': now,
                'reference': ref + ' (Annul. Sortie)',
                'res_model': 'casa.stock.transfer',
                'res_id': rec.id,
            })

            # Reversal: remove from destination
            move_cancel_in = self.env['casa.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.dest_ville,
                'ste_id': rec.dest_ste_id.id if rec.dest_ste_id else False,
                'qty': -rec.qty,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'price_purchase': rec.price_purchase,
                'move_type': 'cancel_entry',
                'state': 'done',
                'date': now,
                'reference': ref + ' (Annul. Entrée)',
                'res_model': 'casa.stock.transfer',
                'res_id': rec.id,
            })

            rec.write({
                'state': 'cancel',
                'move_cancel_out_id': move_cancel_out.id,
                'move_cancel_in_id': move_cancel_in.id,
            })

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_("Seuls les transferts annulés peuvent être remis en brouillon."))
            rec.write({
                'state': 'draft',
                'move_out_id': False,
                'move_in_id': False,
                'move_cancel_out_id': False,
                'move_cancel_in_id': False,
            })
