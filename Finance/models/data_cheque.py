from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class DataCheque(models.Model):
    _name = 'datacheque'
    _description = 'Data chèque'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    chq = fields.Char(string='Chèque', required=True, tracking=True)
    amount = fields.Integer(string='Montant', required=True, tracking=True, group_operator="sum")
    price = fields.Float(string='Prix d’achat', required=True, tracking=True)
    date_emission = fields.Date(string='Date d’émission', tracking=True)
    week = fields.Char(string='Semaine', compute='_compute_week', store=True)
    date_echeance = fields.Date(string='Date d’échéance', tracking=True)
    date_encaissement = fields.Date(string='Date d’encaissement', tracking=True)
    ste_id = fields.Many2one('finance.ste', string='Société', tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénificiaire', tracking=True)
    perso_id = fields.Many2one('finance.perso', string='Personnes', tracking=True)
    facture = fields.Char(string='Facture', compute='_compute_fact', store=True)
    facture_tag = fields.Html(string='Facture', compute='_compute_facture_tag', sanitize=False)
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
    ], string='Garage', tracking=True, required=True)
    state = fields.Selection([
        ('entree', 'Entrée'),
        ('retour', 'Retour'),
    ], string='État', default='entree', tracking=True)

    return_id = fields.Many2one(
        'cal3iyasortie',
        string='Produit retourné',
        tracking=True,
        required=False,
        help="Sortie de stock liée pour un retour"
    )

    stock_id = fields.One2many('cal3iya.stock', 'entry_id', string='Ligne de stock liée', readonly=True)
    # ------------------------------------------------------------
    # BADGE VISUEL
    # ------------------------------------------------------------
    @api.depends('facture_tag')
    def _compute_facture_tag(self):
        for rec in self:
            if rec.diff > 0:
                label = "bénéfice"
                color = "#28a745"
                bg = "rgba(40,167,69,0.12)"
            elif rec.diff < 0:
                label = "perte"
                color = "#dc3545"
                bg = "rgba(220,53,69,0.12)"
            else:
                label = "0"
                color = "#6c757d"  # gris neutre
                bg = "rgba(108,117,125,0.12)"
            rec.benif_perte = (
                f"<span style='display:inline-block;padding:2px 8px;border-radius:12px;"
                f"font-weight:600;background:{bg};color:{color};'>"
                f"{label}"
                f"</span>"
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
            self.garage = sortie.garage
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
    @api.depends('date_emission')
    def _compute_week(self):
        for record in self:
            if record.date_emission:
                record.week = record.date_emission.strftime("%Y-W%W")
            else:
                record.week = False
    
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
        ('unique_lot_dum_garage_state', 'unique(lot, dum, garage, state)',
        'Cette entrée existe déjà. Juste modifiez la quantité.')
    ]

    @api.constrains('lot', 'dum', 'garage', 'state')
    def _check_unique_for_entree(self):
        """Empêche de créer une deuxième entrée réelle sur la même combinaison."""
        for rec in self:
            if rec.state == 'entree':
                existing = self.search([
                    ('id', '!=', rec.id),
                    ('lot', '=', rec.lot),
                    ('dum', '=', rec.dum),
                    ('garage', '=', rec.garage),
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
            self.env['cal3iya.stock'].sudo().create({
                'entry_id': rec.id,
                'name': rec.name,
                'quantity': rec.quantity,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage,
                'price': rec.price,
                'weight': rec.weight,
                'tonnage': rec.tonnage,
                'calibre': rec.calibre,
                'ste_id': rec.ste_id.id,
                'provider_id': rec.provider_id.id,
                'image_1920': rec.image_1920,
            })

        elif rec.state == 'retour':
            stock = self.env['cal3iya.stock'].sudo().search([
                ('lot', '=', rec.lot),
                ('dum', '=', rec.dum),
                ('garage', '=', rec.garage),
            ], limit=1)
            if stock:
                stock.recompute_qty()
        return rec
        
    def write(self, vals):
        res = super().write(vals)

        for rec in self:
            if rec.state == 'entree':
                # 🔗 Chercher la ligne stock liée à cette entrée
                stock = self.env['cal3iya.stock'].sudo().search([('entry_id', '=', rec.id)], limit=1)
                if stock:
                    # 🧩 Mettre à jour la ligne liée
                    stock.write({
                        'name': rec.name,
                        'lot': rec.lot,
                        'dum': rec.dum,
                        'quantity': rec.quantity,
                        'garage': rec.garage,
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
                    self.env['cal3iya.stock'].sudo().create({
                        'entry_id': rec.id,
                        'name': rec.name,
                        'lot': rec.lot,
                        'dum': rec.dum,
                        'quantity': rec.quantity,
                        'garage': rec.garage,
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
                stock = self.env['cal3iya.stock'].sudo().search([('entry_id', '=', rec.id)], limit=1)
                if stock:
                    has_out = self.env['cal3iyasortie'].sudo().search_count([('entry_id', '=', stock.id)]) > 0
                    if has_out:
                        raise UserError("Impossible de supprimer l’entrée: des sorties existent pour le stock lié.")
                    # pas de sorties → on peut supprimer la ligne de stock
                    stock.unlink()

        # Supprimer l’entrée puis recalculer les combos impactées (cas retour)
        combos = [(r.lot, r.dum, r.garage) for r in self]
        res = super().unlink()
        for lot, dum, garage in combos:
            self._recompute_combo(lot, dum, garage)
        return res
    
    def _touch_related_stock_qty(self):
        """Recalcule la quantité de stock pour les combos concernées par self."""
        combos = {(r.lot, r.dum, r.garage) for r in self}
        for lot, dum, garage in combos:
            self._recompute_combo(lot, dum, garage)

    def _recompute_combo(self, lot, dum, garage):
        """Recalcule uniquement pour les retours ou suppression d'entrées."""
        Stock = self.env['cal3iya.stock'].sudo()

        # 🔸 On ignore les combinaisons déjà couvertes par une entrée réelle
        entries = self.search([
            ('lot', '=', lot),
            ('dum', '=', dum),
            ('garage', '=', garage),
            ('state', '=', 'entree')
        ])
        if entries:
            return  # ✅ Rien à recalculer : stock déjà géré via entry_id

        # 🔸 Aucun entry réel → on recalcul ou on supprime le stock orphelin
        orphan = Stock.search([
            ('lot', '=', lot),
            ('dum', '=', dum),
            ('garage', '=', garage)
        ], limit=1)

        if not orphan:
            return

        has_out = self.env['cal3iyasortie'].sudo().search_count([('entry_id', '=', orphan.id)]) > 0
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
         #   entries = self.env['cal3iyaentry'].search([
          #      ('lot', '=', lot),
           #     ('dum', '=', dum),
            #    ('frigo', '=', frigo)
             #   ('ville', '=', ville)
            #])
            #total_entries = sum(e.quantity for e in entries)

            # Si aucune entrée n'existe → on supprime la ligne de stock
#            if not entries:
 #               stock = self.env['cal3iya.stock'].search([
  #                  ('lot', '=', lot),
   #                 ('dum', '=', dum),
    #                ('frigo', '=', frigo)
     #               ('ville', '=', ville)
      #          ])
       #         if stock:
        #            stock.unlink()
         #       continue

            # Calcul de la somme des sorties
          #  sorties = self.env['cal3iyasortie'].search([
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