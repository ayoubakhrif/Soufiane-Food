from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class ProductEntry(models.Model):
    _name = 'kal3iyaentry'
    _description = 'Entrée de stock'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ------------------------------------------------------------
    # CHAMPS
    # ------------------------------------------------------------
    name = fields.Char(string='Nom du produit', required=True, tracking=True)
    quantity = fields.Integer(string='Quantité', required=True, tracking=True, group_operator="sum")
    price = fields.Float(string='Prix d’achat', required=True, tracking=True)
    selling_price = fields.Float(string='Prix de vente', required=True, tracking=True)
    date_entry = fields.Date(string='Date d’entrée', tracking=True)

    lot = fields.Char(string='Lot', required=True, tracking=True)
    dum = fields.Char(string='DUM', required=True, tracking=True)

    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Stock', tracking=True, default='casa')

    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock'),
    ], string='Frigo', tracking=True)

    weight = fields.Float(string='Poids (kg)', required=True, tracking=True)
    tonnage = fields.Float(string='Tonnage (Kg)', compute='_compute_tonnage', store=True)

    mt_achat = fields.Float(string='Mt.Achat', compute='_compute_mt_achat', store=True)

    calibre = fields.Char(string='Calibre', tracking=True)
    driver_id = fields.Many2one('kal3iya.driver',string='Chauffeur', tracking=True)
    cellphone = fields.Char(string='Téléphone', related='driver_id.phone', readonly=True)

    ste_id = fields.Many2one('kal3iya.ste', string='Société', tracking=True)
    provider_id = fields.Many2one('kal3iya.provider', string='Fournisseur', tracking=True)
    client_id = fields.Many2one('kal3iya.client', string='Client', tracking=True)

    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)

    charge_transport = fields.Float(string='Main d’oeuvre', compute='_compute_charge_transport', store=True)

    state = fields.Selection([
        ('entree', 'Entrée'),
        ('retour', 'Retour'),
    ], string='État', default='entree', tracking=True)

    return_id = fields.Many2one(
        'kal3iyasortie',
        string='Produit retourné',
        tracking=True,
        help="Sortie de stock liée pour un retour"
    )

    stock_id = fields.One2many('kal3iya.stock', 'entry_id', string='Ligne de stock liée', readonly=True)

    # ------------------------------------------------------------
    # CALCULS
    # ------------------------------------------------------------
    @api.depends('quantity', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.quantity * rec.weight if rec.quantity and rec.weight else 0.0

    @api.depends('price', 'tonnage')
    def _compute_mt_achat(self):
        for rec in self:
            rec.mt_achat = rec.price * rec.tonnage if rec.price and rec.tonnage else 0.0

    @api.depends('tonnage')
    def _compute_charge_transport(self):
        for rec in self:
            rec.charge_transport = rec.tonnage * 20 if rec.tonnage else 0.0

    # ------------------------------------------------------------
    # CONTRAINTES
    # ------------------------------------------------------------
    @api.constrains('quantity', 'return_id', 'state')
    def _check_return_quantity(self):
        for rec in self:
            if rec.state == 'retour' and rec.return_id and rec.quantity > rec.return_id.quantity:
                raise ValidationError("La quantité retournée ne peut pas dépasser la quantité sortie.")

    _sql_constraints = [
        ('unique_lot_dum_frigo_ville_state',
         'unique(lot, dum, ville, frigo, state)',
         'Cette entrée existe déjà. Modifiez la quantité.')
    ]

    # ------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------
    @api.model
    def create(self, vals):
        rec = super().create(vals)

        # ENTRÉE → créer une ligne de stock
        if rec.state == 'entree':
            self.env['kal3iya.stock'].sudo().create({
                'entry_id': rec.id,
                'name': rec.name,
                'lot': rec.lot,
                'dum': rec.dum,
                'quantity': rec.quantity,
                'frigo': rec.frigo,
                'ville': rec.ville,
                'price': rec.price,
                'weight': rec.weight,
                'tonnage': rec.tonnage,
                'calibre': rec.calibre,
                'ste_id': rec.ste_id.id,
                'provider_id': rec.provider_id.id,
                'image_1920': rec.image_1920,
            })

        # RETOUR → ajouter quantité au stock original
        elif rec.state == 'retour' and rec.return_id:
            stock = rec.return_id.entry_id
            if not stock:
                raise UserError("Impossible : aucune ligne de stock liée à la sortie.")
            stock.recompute_qty()

        return rec

    # ------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)

        for rec in self:
            if rec.state == 'entree':
                stock = self.env['kal3iya.stock'].sudo().search([('entry_id', '=', rec.id)], limit=1)
                if stock:
                    stock.write({
                        'name': rec.name,
                        'lot': rec.lot,
                        'dum': rec.dum,
                        'quantity': rec.quantity,
                        'frigo': rec.frigo,
                        'ville': rec.ville,
                        'price': rec.price,
                        'weight': rec.weight,
                        'tonnage': rec.tonnage,
                        'calibre': rec.calibre,
                        'ste_id': rec.ste_id.id,
                        'provider_id': rec.provider_id.id,
                        'image_1920': rec.image_1920,
                    })
                    stock.recompute_qty()

            elif rec.state == 'retour' and rec.return_id:
                stock = rec.return_id.entry_id
                if stock:
                    stock.recompute_qty()

        return res

    # ------------------------------------------------------------
    # UNLINK
    # ------------------------------------------------------------
    def unlink(self):
        for rec in self:
            if rec.state == 'entree':
                stock = self.env['kal3iya.stock'].sudo().search([('entry_id', '=', rec.id)], limit=1)
                if stock:
                    has_out = self.env['kal3iyasortie'].sudo().search_count([('entry_id', '=', stock.id)]) > 0
                    if has_out:
                        raise UserError("Impossible de supprimer : des sorties existent.")
                    stock.unlink()

            # Si retour → recalculer le stock origine
            if rec.state == 'retour' and rec.return_id:
                stock = rec.return_id.entry_id
                if stock:
                    super(ProductEntry, rec).unlink()
                    stock.recompute_qty()
                    continue

        return super().unlink()
