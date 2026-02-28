from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class Kal3iyaStockTransfer(models.Model):
    _name = 'kal3iya.stock.transfer'
    _description = 'Transfert de stock'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string="Référence",
        default=lambda self: self.env['ir.sequence'].next_by_code('kal3iya.stock.transfer'),
        readonly=True
    )

    date = fields.Date(
        string="Date de transfert",
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    # ─────────────────────────────
    # STOCKS
    # ─────────────────────────────
    source_ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string="Stock source", required=True, tracking=True)

    dest_ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string="Stock destination", required=True, tracking=True)

    # ─────────────────────────────
    # PRODUIT (comme sortie)
    # ─────────────────────────────
    stock_id = fields.Many2one(
        'kal3iya.stock',
        string="Produit en stock",
        required=True,
        tracking=True,
        domain="[('quantity', '>', 0)]"
    )

    product_id = fields.Many2one(
        related='stock_id.product_id',
        store=True,
        readonly=True
    )
    lot = fields.Char(related='stock_id.lot', store=True, readonly=True)
    dum = fields.Char(related='stock_id.dum', store=True, readonly=True)
    price = fields.Float(related='stock_id.price', store=True, readonly=True)
    weight = fields.Float(related='stock_id.weight', store=True, readonly=True)
    calibre = fields.Char(related='stock_id.calibre', store=True, readonly=True)

    quantity = fields.Float(
        string="Quantité à transférer",
        required=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
    ], default='draft', tracking=True)

    @api.onchange('source_ville')
    def _onchange_source_ville(self):
        self.stock_id = False
        if self.source_ville:
            return {
                'domain': {
                    'stock_id': [
                        ('ville', '=', self.source_ville),
                        ('quantity', '>', 0)
                    ]
                }
            }

    @api.constrains('quantity', 'stock_id')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError("La quantité doit être supérieure à zéro.")
            if rec.stock_id and rec.quantity > rec.stock_id.quantity:
                raise ValidationError(
                    "Quantité insuffisante dans le stock source."
                )

    def action_confirm(self):
        Sortie = self.env['kal3iyasortie'].sudo()
        Entry = self.env['kal3iyaentry'].sudo()

        for rec in self:
            if rec.source_ville == rec.dest_ville:
                raise UserError("Le stock source et destination doivent être différents.")

            stock_src = rec.stock_id
            internal_client = rec._get_internal_client()

            # 1️⃣ SORTIE INTERNE
            Sortie.create({
                'entry_id': stock_src.id,
                'quantity': rec.quantity,
                'selling_price': stock_src.price,
                'date_exit': rec.date,
                'client_id': internal_client.id,  # ✅ OBLIGATOIRE
                'ville': rec.source_ville,
            })

            # 2️⃣ ENTRÉE INTERNE
            Entry.create({
                'product_id': stock_src.product_id.id,
                'quantity': rec.quantity,
                'price': stock_src.price,
                'selling_price': stock_src.price,
                'date_entry': rec.date,
                'lot': stock_src.lot,
                'dum': stock_src.dum,
                'ville': rec.dest_ville,
                'frigo': stock_src.frigo,
                'weight': stock_src.weight,
                'calibre': stock_src.calibre,
                'ste_id': stock_src.ste_id.id,
                'provider_id': stock_src.provider_id.id,
                'state': 'entree',
            })

            rec.state = 'done'


    def _get_internal_client(self):
        Client = self.env['kal3iya.client'].sudo()
        client = Client.search([('name', '=', 'Transfert interne')], limit=1)
        if not client:
            client = Client.create({'name': 'Transfert interne', 'is_internal': True,})
        return client
