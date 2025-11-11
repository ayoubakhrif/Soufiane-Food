from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductEntry(models.Model):
    _name = 'kal3iyaentry'
    _description = 'Entrée de stock'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom du produit', required=True, tracking=True)
    quantity = fields.Integer(string='Quantité', required=True, tracking=True)
    price = fields.Float(string='Prix d’achat', required=True, tracking=True)
    selling_price = fields.Float(string='Prix de vente', required=True, tracking=True)
    date_entry = fields.Date(string='Date d’entrée', tracking=True)
    lot = fields.Char(string='Lot', required=True, tracking=True)
    dum = fields.Char(string='DUM', required=True, tracking=True)
    stock = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Stock', tracking=True, default='casa')
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
    ], string='Frigo', tracking=True)
    weight = fields.Float(string='Poids (kg)', required=True, tracking=True)
    tonnage = fields.Float(string='Tonnage (Kg)', compute='_compute_tonnage', store=True)
    total_price = fields.Integer(string='total', compute='_compute_total_price', store=True)
    calibre = fields.Char(string='Calibre', tracking=True)
    driver_id = fields.Many2one('kal3iya.driver',string='Chauffeur' , tracking=True)
    cellphone = fields.Char(string='Téléphone', related='driver_id.phone', readonly=True)
    ste_id = fields.Many2one('kal3iya.ste', string='Société', tracking=True)
    provider_id = fields.Many2one('kal3iya.provider', string='Fournisseur', tracking=True)
    client_id = fields.Many2one('kal3iya.client', string='Client', tracking=True)
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)
    charge_transport = fields.Integer(string='Main d’oeuvre', compute='_compute_charge_transport', store=True)


    state = fields.Selection([
        ('entree', 'Entrée'),
        ('retour', 'Retour'),
    ], string='État', default='entree', tracking=True)

    return_id = fields.Many2one(
        'kal3iyasortie',
        string='Produit retourné',
        tracking=True,
        required=False,
        help="Sortie de stock liée pour un retour"
    )

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
    # ONCHANGE SUR RETOUR
    # ------------------------------------------------------------
    @api.onchange('return_id')
    def _onchange_return_id(self):
        """Remplit automatiquement les infos à partir de la sortie sélectionnée."""
        if self.return_id:
            sortie = self.return_id
            self.lot = sortie.lot
            self.dum = sortie.dum
            self.name = sortie.name
            self.weight = sortie.weight
            self.calibre = sortie.calibre
            self.ste_id = sortie.ste_id
            self.provider_id = sortie.provider_id
            self.client_id = sortie.client_id
            self.frigo = sortie.frigo
            self.image_1920 = sortie.image_1920
            self.selling_price = sortie.selling_price
        else:
            # Si aucun retour sélectionné, ne rien écraser
            pass

    # ------------------------------------------------------------
    # Changer return_id selon client
    # ------------------------------------------------------------
    @api.onchange('client_id')
    def _onchange_client_id(self):
        """Filtrer les sorties selon le client sélectionné"""
        if self.client_id:
            return {
                'domain': {
                    'return_id': [('client_id', '=', self.client_id.id)]
                }
            }
        else:
            return {
                'domain': {
                    'return_id': []
                }
            }
    
    # ------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------
    @api.depends('quantity', 'weight')
    def _compute_tonnage(self):
        for record in self:
            record.tonnage = record.quantity * record.weight if record.quantity and record.weight else 0.0

    @api.depends('price', 'tonnage')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.price * record.tonnage if record.price and record.tonnage else 0.0

    @api.depends('tonnage')
    def _compute_charge_transport(self):
        for record in self:
            record.charge_transport = record.tonnage * 20 if record.tonnage else 0.0

    # ------------------------------------------------------------
    # CONTRAINTE D’UNICITÉ
    # ------------------------------------------------------------
    _sql_constraints = [
        ('unique_lot_dum_frigo', 'unique(lot, dum, frigo, state)',
         'Une entrée avec le même Lot, DUM et frigo existe déjà !')
    ]

    # ------------------------------------------------------------
    # CONTRAINTE RETOUR
    # ------------------------------------------------------------
    @api.constrains('quantity', 'return_id', 'state')
    def _check_return_quantity(self):
        for rec in self:
            if rec.state == 'retour' and rec.return_id:
                if rec.quantity > rec.return_id.quantity:
                    raise ValidationError(
                        "❌ La quantité retournée ne peut pas dépasser la quantité sortie."
                    )

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
        lots_to_update = [(rec.lot, rec.dum, rec.frigo) for rec in self]
        res = super().unlink()
        # Recalculer après suppression
        for lot, dum, frigo in lots_to_update:
            self._recalculate_stock(lot, dum, frigo)
        return res

    # ------------------------------------------------------------
    # LOGIQUE DU STOCK
    # ------------------------------------------------------------
    def _recalculate_stock(self, lot=None, dum=None, frigo=None):
        if self and all(r.exists() for r in self):
            lots = [(rec.lot, rec.dum, rec.frigo) for rec in self]
        elif lot and dum and frigo:
            lots = [(lot, dum, frigo)]
        else:
            return


        for lot, dum, frigo in lots:
            # Chercher l’entrée correspondante
            entries = self.env['kal3iyaentry'].search([
                ('lot', '=', lot),
                ('dum', '=', dum),
                ('frigo', '=', frigo)
            ])
            total_entries = sum(e.quantity for e in entries)

            # Si aucune entrée n'existe → on supprime la ligne de stock
            if not entries:
                stock = self.env['kal3iya.stock'].search([
                    ('lot', '=', lot),
                    ('dum', '=', dum),
                    ('frigo', '=', frigo)
                ])
                if stock:
                    stock.unlink()
                continue

            # Calcul de la somme des sorties
            sorties = self.env['kal3iyasortie'].search([
                ('lot', '=', lot),
                ('dum', '=', dum),
                ('frigo', '=', frigo)
            ])
            total_sorties = sum(s.quantity for s in sorties)

            # Calcul du stock
            stock_actuel = total_entries - total_sorties

            ref_entry = entries.sorted(lambda e: e.id, reverse=True)[0]

            # Mettre à jour ou créer la ligne correspondante
            stock = self.env['kal3iya.stock'].search([
                ('lot', '=', lot),
                ('dum', '=', dum),
                ('frigo', '=', frigo)
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
                    'frigo': frigo,
                })
                self.env['kal3iya.stock'].create(valeurs)

            if stock.quantity == 0 and stock.active:
                stock.active = False
            elif stock.quantity > 0 and not stock.active:
                stock.active = True

        self.env['kal3iya.stock'].update_stock_archive_status()