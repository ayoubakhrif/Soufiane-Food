from odoo import models, fields, api

class ProductEntry(models.Model):
    _name = 'kal3iyaentry'
    _description = 'Entrée de stock'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom du produit', required=True, tracking=True)
    quantity = fields.Integer(string='Quantité', required=True, tracking=True)
    price = fields.Float(string='Prix d’achat', required=True, tracking=True)
    date_entry = fields.Date(string='Date d’entrée', tracking=True)
    lot = fields.Char(string='Lot', required=True, tracking=True)
    dum = fields.Char(string='DUM', required=True, tracking=True)
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
    ], tracking=True)
    weight = fields.Float(string='Poids (kg)', required=True, tracking=True)
    tonnage = fields.Float(string='Tonnage (Kg)', compute='_compute_tonnage', store=True)
    calibre = fields.Char(string='Calibre', tracking=True)
    driver_id = fields.Many2one('kal3iya.driver', tracking=True)
    cellphone = fields.Char(string='Téléphone', related='driver_id.phone', readonly=True)
    ste_id = fields.Many2one('kal3iya.ste', tracking=True)
    provider_id = fields.Many2one('kal3iya.provider', tracking=True)
    client_id = fields.Many2one('kal3iya.client', tracking=True)
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)

    state = fields.Selection([
        ('entree', 'Entrée'),
        ('retour', 'Retour'),
    ], string='État', default='entree', tracking=True)

    state_badge = fields.Html(string='État (badge)', compute='_compute_state_badge', sanitize=False)

    # ------------------------------------------------------------
    # BADGE VISUEL
    # ------------------------------------------------------------
    def _compute_state_badge(self):
        for rec in self:
            label = dict(self._fields['state'].selection).get(rec.state, '') or ''
            color = "#28a745" if rec.state == 'entree' else "#dc3545"
            bg = "rgba(40,167,69,0.12)" if rec.state == 'entree' else "rgba(220,53,69,0.12)"
            rec.state_badge = (
                f"<span style='display:inline-block;padding:2px 8px;border-radius:12px;"
                f"font-weight:600;background:{bg};color:{color};'>{label}</span>"
            )

    # ------------------------------------------------------------
    # TONNAGE
    # ------------------------------------------------------------
    @api.depends('quantity', 'weight')
    def _compute_tonnage(self):
        for record in self:
            record.tonnage = record.quantity * record.weight if record.quantity and record.weight else 0.0

    # ------------------------------------------------------------
    # CONTRAINTE D’UNICITÉ
    # ------------------------------------------------------------
    _sql_constraints = [
        ('unique_lot_dum_garage', 'unique(lot, dum, garage, state)',
         'Une entrée avec le même Lot, DUM et Garage existe déjà !')
    ]

    # ------------------------------------------------------------
    # CRUD OVERRIDES
    # ------------------------------------------------------------
    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._recalculate_stock()
        return record

    def write(self, vals):
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
                'ste_id': ref_entry.ste_id.id,
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