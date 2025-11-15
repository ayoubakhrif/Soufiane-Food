from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

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
    driver_id = fields.Many2one('kal3iya.driver',string='Chauffeur' , tracking=True)
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
        required=False,
        help="Sortie de stock liée pour un retour"
    )
    stock_id = fields.One2many('kal3iya.stock', 'entry_id', string='Ligne de stock liée', readonly=True)
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
            self.ville = sortie.ville
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
    def _compute_mt_achat(self):
        for record in self:
            record.mt_achat = record.price * record.tonnage if record.price and record.tonnage else 0.0

    @api.depends('tonnage')
    def _compute_charge_transport(self):
        for record in self:
            record.charge_transport = record.tonnage * 20 if record.tonnage else 0.0

    # ------------------------------------------------------------
    # CONTRAINTE D’UNICITÉ
    # ------------------------------------------------------------
    _sql_constraints = [
        ('unique_lot_dum_frigo_ville_state', 'unique(lot, dum, ville, frigo, state)',
        'Cette entrée existe déjà. Juste modifiez la quantité.')
    ]

    @api.constrains('lot', 'dum', 'frigo', 'ville', 'state')
    def _check_unique_for_entree(self):
        """Empêche de créer une deuxième entrée réelle sur la même combinaison."""
        for rec in self:
            if rec.state == 'entree':
                existing = self.search([
                    ('id', '!=', rec.id),
                    ('lot', '=', rec.lot),
                    ('dum', '=', rec.dum),
                    ('frigo', '=', rec.frigo),
                    ('ville', '=', rec.ville),
                    ('state', '=', 'entree'),
                ], limit=1)
                if existing:
                    raise ValidationError("Cette entrée existe déjà. Modifiez la quantité au lieu d’en créer une nouvelle.")

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
        rec = super().create(vals)
        # 1) Si entrée réelle → créer SA ligne de stock (1:1)
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

        elif rec.state == 'retour':
            stock = self.env['kal3iya.stock'].sudo().search([
                ('lot', '=', rec.lot),
                ('dum', '=', rec.dum),
                ('frigo', '=', rec.frigo),
                ('ville', '=', rec.ville),
            ], limit=1)
            if stock:
                stock.recompute_qty()
        return rec
        
    def write(self, vals):
        res = super().write(vals)

        for rec in self:
            if rec.state == 'entree':
                # 🔗 Chercher la ligne stock liée à cette entrée
                stock = self.env['kal3iya.stock'].sudo().search([('entry_id', '=', rec.id)], limit=1)
                if stock:
                    # 🧩 Mettre à jour la ligne liée
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
                else:
                    # Cas rare : si la ligne a été supprimée manuellement
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
            else:
                # 🔄 Pour les retours → recalcul classique
                rec._touch_related_stock_qty()

        return res


    def unlink(self):
        for rec in self:
            if rec.state == 'entree':
                # Entrée réelle: sa ligne stock ne peut être supprimée que si aucune sortie liée
                stock = self.env['kal3iya.stock'].sudo().search([('entry_id', '=', rec.id)], limit=1)
                if stock:
                    has_out = self.env['kal3iyasortie'].sudo().search_count([('entry_id', '=', stock.id)]) > 0
                    if has_out:
                        raise UserError("Impossible de supprimer l’entrée: des sorties existent pour le stock lié.")
                    # pas de sorties → on peut supprimer la ligne de stock
                    stock.unlink()

        # Supprimer l’entrée puis recalculer les combos impactées (cas retour)
        combos = [(r.lot, r.dum, r.frigo, r.ville) for r in self]
        res = super().unlink()
        for lot, dum, frigo, ville in combos:
            self._recompute_combo(lot, dum, frigo, ville)
        return res
    
    def _touch_related_stock_qty(self):
        """Recalcule la quantité de stock pour les combos concernées par self."""
        combos = {(r.lot, r.dum, r.frigo, r.ville) for r in self}
        for lot, dum, frigo, ville in combos:
            self._recompute_combo(lot, dum, frigo, ville)

    def _recompute_combo(self, lot, dum, frigo, ville):
        """Recalcule uniquement pour les retours ou suppression d'entrées."""
        Stock = self.env['kal3iya.stock'].sudo()

        # 🔸 On ignore les combinaisons déjà couvertes par une entrée réelle
        entries = self.search([
            ('lot', '=', lot),
            ('dum', '=', dum),
            ('frigo', '=', frigo),
            ('ville', '=', ville),
            ('state', '=', 'entree')
        ])
        if entries:
            return  # ✅ Rien à recalculer : stock déjà géré via entry_id

        # 🔸 Aucun entry réel → on recalcul ou on supprime le stock orphelin
        orphan = Stock.search([
            ('lot', '=', lot),
            ('dum', '=', dum),
            ('frigo', '=', frigo),
            ('ville', '=', ville)
        ], limit=1)

        if not orphan:
            return

        has_out = self.env['kal3iyasortie'].sudo().search_count([('entry_id', '=', orphan.id)]) > 0
        if has_out:
            orphan.recompute_qty()  # garde mais met à jour la quantité
        else:
            orphan.unlink()


    # ------------------------------------------------------------
    # LOGIQUE DU STOCK
    # ------------------------------------------------------------
    #def _recalculate_stock(self, lot=None, dum=None, frigo=None):
     #   if self and all(r.exists() for r in self):
      #      lots = [(rec.lot, rec.dum, rec.frigo, rec.ville) for rec in self]
       # elif lot and dum and frigo and ville:
        #    lots = [(lot, dum, frigo, ville)]
        #else:
         #   return


        #for lot, dum, frigo, ville in lots:
            # Chercher l’entrée correspondante
         #   entries = self.env['kal3iyaentry'].search([
          #      ('lot', '=', lot),
           #     ('dum', '=', dum),
            #    ('frigo', '=', frigo)
             #   ('ville', '=', ville)
            #])
            #total_entries = sum(e.quantity for e in entries)

            # Si aucune entrée n'existe → on supprime la ligne de stock
#            if not entries:
 #               stock = self.env['kal3iya.stock'].search([
  #                  ('lot', '=', lot),
   #                 ('dum', '=', dum),
    #                ('frigo', '=', frigo)
     #               ('ville', '=', ville)
      #          ])
       #         if stock:
        #            stock.unlink()
         #       continue

            # Calcul de la somme des sorties
          #  sorties = self.env['kal3iyasortie'].search([
           #     ('lot', '=', lot),
            #    ('dum', '=', dum),
             #   ('frigo', '=', frigo)
              #  ('ville', '=', ville)
            #])
#            total_sorties = sum(s.quantity for s in sorties)

           # Calcul du stock
#            stock_actuel = total_entries - total_sorties

#            ref_entry = entries.sorted(lambda e: e.id, reverse=True)[0]

            # Mettre à jour ou créer la ligne correspondante
 #           stock = self.env['kal3iya.stock'].search([
  #              ('lot', '=', lot),
   #             ('dum', '=', dum),
    #            ('frigo', '=', frigo)
     #           ('ville', '=', ville)
      #      ], limit=1)

       #     valeurs = {
        #        'name': ref_entry.name,
         #       'quantity': stock_actuel,
          #      'price': ref_entry.price,
           #     'weight': ref_entry.weight,
            #    'tonnage': ref_entry.tonnage,
             #   'calibre': ref_entry.calibre,
              #  'ste_id': ref_entry.ste_id.id,
               # 'provider_id': ref_entry.provider_id.id,
                #'image_1920' : ref_entry.image_1920,
            #}

            #if stock:
             #   stock.write(valeurs)
            #else:
             #   valeurs.update({
              #      'lot': lot,
               #     'dum': dum,
                #    'frigo': frigo,
                 #   'ville': ville,
#                })
 #               self.env['kal3iya.stock'].create(valeurs)

#            if stock.quantity == 0 and stock.active:
 #               stock.active = False
  #          elif stock.quantity > 0 and not stock.active:
   #             stock.active = True

    #    self.env['kal3iya.stock'].update_stock_archive_status()