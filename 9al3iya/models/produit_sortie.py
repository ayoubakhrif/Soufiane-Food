from odoo import api, models, fields
from odoo.exceptions import UserError

class ProduitExit(models.Model):
    _name = 'cal3iyasortie'
    _description = 'Sortie de stock'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    entry_id = fields.Many2one(
        'cal3iya.stock',
        string='Produits en stocks',
        required=True,
        help="Entrée de stock correspondante",
        tracking=True,
        ondelete='restrict', index=True
    )

    lot = fields.Char(string='Lot', related='entry_id.lot', store=True, readonly=True)
    dum = fields.Char(string='DUM', related='entry_id.dum', store=True, readonly=True)
    name = fields.Char(string='Nom du produit', related='entry_id.name', store=True, readonly=True)
    weight = fields.Float(string='Poids (kg)', related='entry_id.weight', store=True, readonly=True)
    calibre = fields.Char(string='Calibre', related='entry_id.calibre', store=True, readonly=True)
    ste_id = fields.Many2one(
        'cal3iya.ste', 
        string='Société',
        related='entry_id.ste_id', 
        store=True, 
        readonly=False
    )
    provider_id = fields.Many2one(
        'cal3iya.provider', 
        string='Fournisseur',
        related='entry_id.provider_id', 
        store=True, 
        readonly=False
    )
    quantity = fields.Integer(string='Qté', required=True, tracking=True)
    selling_price = fields.Float(string='Prix de vente', required=True, tracking=True)
    date_exit = fields.Date(string='Date de sortie', required=True, tracking=True)
    tonnage = fields.Float(string='Tonnage(Kg)', compute='_compute_tonnage', store=True, readonly=True)
    driver_id = fields.Many2one('cal3iya.driver', string='Chauffeur', tracking=True)
    cellphone = fields.Char(string='Téléphone', related='driver_id.phone', readonly=True)
    client_id = fields.Many2one('cal3iya.client', tracking=True)
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
    ], string='Stock', tracking=True)
    charge_transport = fields.Integer(string='Main d’oeuvre', compute='_compute_charge_transport', store=True)
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

    @api.depends('tonnage')
    def _compute_charge_transport(self):
        for record in self:
            record.charge_transport = record.tonnage * 0.02 if record.tonnage else 0.0

    # ------------------------------------------------------------
    # AFFICHAGE
    # ------------------------------------------------------------
    display_name = fields.Char(
        string='Nom affiché', 
        compute='_compute_display_name', 
        store=False
    )

    @api.depends('client_id', 'name', 'lot', 'dum', 'quantity')
    def _compute_display_name(self):
        """Construit le texte affiché dans les menus déroulants"""
        for rec in self:
            client = rec.client_id.name or ''
            produit = rec.name or ''
            lot = rec.lot or ''
            dum = rec.dum or ''
            qty = rec.quantity or 0
            rec.display_name = f"{client} - {produit} - Lot {lot} - DUM {dum} - Qté {qty}"

    def name_get(self):
        """Personnaliser le nom affiché dans les listes déroulantes"""
        result = []
        for rec in self:
            client = rec.client_id.name or ''
            produit = rec.name or ''
            lot = rec.lot or ''
            dum = rec.dum or ''
            qty = rec.quantity or 0
            name = f"{client} - {produit} - Lot {lot} - DUM {dum} - Qté {qty}"
            result.append((rec.id, name))
        return result

    # ------------------------------------------------------------
    # CRUD OVERRIDES
    # ------------------------------------------------------------
    @api.model
    def create(self, vals):
        stock = self.env['cal3iya.stock'].browse(vals.get('entry_id'))
        if stock and vals.get('quantity', 0.0) > stock.quantity:
            raise UserError(f"Stock insuffisant: demande={vals.get('quantity')} > disponible={stock.quantity}.")
        rec = super().create(vals)
        stock.recompute_qty()
        return rec

    def write(self, vals):
        # Vérif basique sur dépassement (optionnel, on peut autoriser la modif puis recompute_qty refusera via process métier)
        for r in self:
            if 'quantity' in vals:
                new_q = vals['quantity']
                # quantité dispo = qty_actuelle + qty_sortie_courante (qu’on s’apprête à remplacer)
                avail = r.entry_id.quantity + (r.quantity or 0.0)
                if new_q > avail:
                    raise UserError(f"Impossible: demande={new_q} > disponible={avail}.")
        res = super().write(vals)
        # Recalculer la/les lignes touchées
        for r in self:
            r.entry_id.recompute_qty()
        return res

    def unlink(self):
        # Retours liés ? Si tu gères des retours par lien Many2one, bloque ici.
        # Exemple: returns = self.env['cal3iyaentry'].search_count([('return_id', 'in', self.ids)]) > 0
        # if returns: raise UserError("Supprimer d’abord les retours liés.")
        stocks = self.mapped('entry_id')
        res = super().unlink()
        stocks.recompute_qty()
        return res

    # ------------------------------------------------------------
    # LOGIQUE DU STOCK
    # ------------------------------------------------------------
#    def _recalculate_stock(self, lot=None, dum=None, frigo=None):
#        if self and all(r.exists() for r in self):
#            lots = [(rec.lot, rec.dum, rec.frigo) for rec in self]
#        elif lot and dum and frigo:
#            lots = [(lot, dum, frigo)]
#        else:
#            return


#        for lot, dum, frigo, ville in lots:
            # Chercher l’entrée correspondante
#            entries = self.env['kal3iyaentry'].search([
#                ('lot', '=', lot),
#                ('dum', '=', dum),
#                ('frigo', '=', frigo)
#                ('ville', '=', ville)
#            ])
#            total_entries = sum(e.quantity for e in entries)

            # Si aucune entrée n'existe → on supprime la ligne de stock
#            if not entries:
#                stock = self.env['kal3iya.stock'].search([
#                    ('lot', '=', lot),
#                    ('dum', '=', dum),
#                    ('frigo', '=', frigo)
 #                   ('ville', '=', ville)
#                ])
#                if stock:
#                    stock.unlink()
 #               continue

            # Calcul de la somme des sorties
#            sorties = self.env['kal3iyasortie'].search([
#                ('lot', '=', lot),
#                ('dum', '=', dum),
#                ('frigo', '=', frigo)
 #               ('ville', '=', ville)
  #          ])
 #           total_sorties = sum(s.quantity for s in sorties)

            # Calcul du stock
#            stock_actuel = total_entries - total_sorties

#            ref_entry = entries.sorted(lambda e: e.id, reverse=True)[0]

            # Mettre à jour ou créer la ligne correspondante
#            stock = self.env['kal3iya.stock'].search([
#                ('lot', '=', lot),
#                ('dum', '=', dum),
#                ('frigo', '=', frigo)
#                ('ville', '=', ville)
#            ], limit=1)

#            valeurs = {
#                'name': ref_entry.name,
#                'quantity': stock_actuel,
#                'price': ref_entry.price,
#                'weight': ref_entry.weight,
#                'tonnage': ref_entry.tonnage,
#                'calibre': ref_entry.calibre,
#                'ste_id': ref_entry.ste_id,
#                'provider_id': ref_entry.provider_id.id,
#                'image_1920' : ref_entry.image_1920,
#            }

#            if stock:
#                stock.write(valeurs)
#            else:
#                valeurs.update({
#                    'lot': lot,
#                    'dum': dum,
#                    'frigo': frigo,
#                    'ville': ville,
#                })
#                self.env['cal3iya.stock'].create(valeurs)

#            if stock.quantity == 0 and stock.active:
#                stock.active = False
#            elif stock.quantity > 0 and not stock.active:
#                stock.active = True

#        self.env['cal3iya.stock'].update_stock_archive_status()