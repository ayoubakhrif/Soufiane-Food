from odoo import api, models, fields
from odoo.exceptions import UserError

class ProductExit(models.Model):
    _name = 'kal3iyasortie'
    _description = 'Sortie de stock'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    entry_id = fields.Many2one(
        'kal3iya.stock',
        string='Produits en stocks',
        required=True,
        help="Entrée de stock correspondante",
        tracking=True
    )

    lot = fields.Char(string='Lot', related='entry_id.lot', store=True, readonly=True)
    dum = fields.Char(string='DUM', related='entry_id.dum', store=True, readonly=True)
    name = fields.Char(string='Nom du produit', related='entry_id.name', store=True, readonly=True)
    weight = fields.Float(string='Poids (kg)', related='entry_id.weight', store=True, readonly=True)
    calibre = fields.Char(string='Calibre', related='entry_id.calibre', store=True, readonly=True)
    ste_id = fields.Many2one(
        'kal3iya.ste', 
        string='Société',
        related='entry_id.ste_id', 
        store=True, 
        readonly=False
    )
    provider_id = fields.Many2one(
        'kal3iya.provider', 
        string='Fournisseur',
        related='entry_id.provider_id', 
        store=True, 
        readonly=False
    )
    quantity = fields.Integer(string='Qté', required=True, tracking=True)
    price = fields.Float(string='Prix de vente', required=True, tracking=True)
    date_exit = fields.Date(string='Date de sortie', required=True, tracking=True)
    tonnage = fields.Float(string='Tonnage(Kg)', compute='_compute_tonnage', store=True, readonly=True)
    driver_id = fields.Many2one('kal3iya.driver', string='Chauffeur', tracking=True)
    cellphone = fields.Char(string='Téléphone', related='driver_id.phone', readonly=True)
    client_id = fields.Many2one('kal3iya.client', tracking=True)
    client2 = fields.Selection([('soufiane', 'Soufiane'), ('hamza', 'Hamza'),], string='Client 2', tracking=True)
    indirect = fields.Boolean(string='S/H', default=False)
    garage = fields.Selection([
        ('garage1', 'Garage 1'),
        ('garage2', 'Garage 2'),
        ('garage3', 'Garage 3'),
        ('garage4', 'Garage 4'),
        ('garage5', 'Garage 5'),
        ('garage6', 'Garage 6'),
        ('garage7', 'Garage 7'),
        ('garage8', 'Garage 8'),
        ('terrasse', 'Terrasse'),
    ], string='Garage', related='entry_id.garage', store=True, readonly=False, tracking=True)
    image_1920 = fields.Image(string="Image", related='entry_id.image_1920', readonly=True, store=False)
    drive_file_url = fields.Char(string="Lien Google Drive", readonly=True, copy=False)
    drive_file_id = fields.Char(string="ID Fichier Drive", readonly=True, copy=False)

    # ------------------------------------------------------------
    # CALCUL DU TONNAGE
    # ------------------------------------------------------------
    @api.depends('quantity', 'weight')
    def _compute_tonnage(self):
        for record in self:
            record.tonnage = record.quantity * record.weight if record.quantity and record.weight else 0.0

    # ------------------------------------------------------------
    # CRUD OVERRIDES
    # ------------------------------------------------------------
    @api.model
    def create(self, vals):
        entry_id = vals.get('entry_id')
        quantity_sortie = vals.get('quantity', 0)

        if entry_id:
            stock = self.env['kal3iya.stock'].browse(entry_id)
            if quantity_sortie > stock.quantity:
                raise UserError(
                    f"🚫 Stock insuffisant:\n"
                    f"Vous essayez de sortir {quantity_sortie} unités alors qu’il ne reste que {stock.quantity} en stock."
                )

        record = super().create(vals)
        record._recalculate_stock()
        return record

    def write(self, vals):
        for rec in self:
            new_quantity = vals.get('quantity', rec.quantity)
            stock = rec.entry_id

            available_qty = stock.quantity + rec.quantity
            if new_quantity > available_qty:
                raise UserError(
                    f"❌ Impossible de modifier la sortie :\n"
                    f"La quantité demandée ({new_quantity}) dépasse le stock disponible ({stock.quantity})."
                )

        res = super().write(vals)
        self._recalculate_stock()
        return res

    def unlink(self):
        # Sauvegarder les infos avant suppression
        lots_to_update = [(rec.lot, rec.dum, rec.garage) for rec in self]
        res = super().unlink()
        # Recalculer après suppression
        for lot, dum, garage in lots_to_update:
            self._recalculate_stock(lot, dum, garage)
        return res

    # ------------------------------------------------------------
    # LOGIQUE DU STOCK
    # ------------------------------------------------------------
    def _recalculate_stock(self, lot=None, dum=None, garage=None):
        if self and all(r.exists() for r in self):
            lots = [(rec.lot, rec.dum, rec.garage) for rec in self]
        elif lot and dum and garage:
            lots = [(lot, dum, garage)]
        else:
            return


        for lot, dum, garage in lots:
            # Chercher l’entrée correspondante
            entries = self.env['kal3iyaentry'].search([
                ('lot', '=', lot),
                ('dum', '=', dum),
                ('garage', '=', garage)
            ])
            total_entries = sum(e.quantity for e in entries)

            # Si aucune entrée n'existe → on supprime la ligne de stock
            if not entries:
                stock = self.env['kal3iya.stock'].search([
                    ('lot', '=', lot),
                    ('dum', '=', dum),
                    ('garage', '=', garage)
                ])
                if stock:
                    stock.unlink()
                continue

            # Calcul de la somme des sorties
            sorties = self.env['kal3iyasortie'].search([
                ('lot', '=', lot),
                ('dum', '=', dum),
                ('garage', '=', garage)
            ])
            total_sorties = sum(s.quantity for s in sorties)

            # Calcul du stock
            stock_actuel = total_entries - total_sorties

            ref_entry = entries.sorted(lambda e: e.id, reverse=True)[0]

            # Mettre à jour ou créer la ligne correspondante
            stock = self.env['kal3iya.stock'].search([
                ('lot', '=', lot),
                ('dum', '=', dum),
                ('garage', '=', garage)
            ], limit=1)

            valeurs = {
                'name': ref_entry.name,
                'quantity': stock_actuel,
                'price': ref_entry.price,
                'weight': ref_entry.weight,
                'tonnage': ref_entry.tonnage,
                'calibre': ref_entry.calibre,
                'ste_id': ref_entry.ste_id,
                'provider_id': ref_entry.provider_id.id,
                'image_1920' : ref_entry.image_1920,
            }

            if stock:
                stock.write(valeurs)
            else:
                valeurs.update({
                    'lot': lot,
                    'dum': dum,
                    'garage': garage,
                })
                self.env['kal3iya.stock'].create(valeurs)

            if stock.quantity == 0 and stock.active:
                stock.active = False
            elif stock.quantity > 0 and not stock.active:
                stock.active = True

        self.env['kal3iya.stock'].update_stock_archive_status()