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
    # ------------------------------------------------------------
    # BADGE VISUEL
    # ------------------------------------------------------------
    @api.depends('facture_tag', 'facture')
    def _compute_facture_tag(self):
        for rec in self:

            factur = rec.facture or ""  # nom de la facture

            # --- Conditions selon ta demande ---
            if factur.startswith("F/"):           # commence par F/
                label = factur
                color = "#28a745"  # vert
                bg = "rgba(40,167,69,0.12)"

            elif factur == "M":                   # exactement = M
                label = factur
                color = "#dc3545"  # rouge
                bg = "rgba(220,53,69,0.12)"

            elif factur == "Bureau":             # exactement = Bureau
                label = factur
                color = "#007bff"  # bleu
                bg = "rgba(0,123,255,0.12)"

            else:                                  # tout le reste
                label = factur
                color = "#6c757d"  # gris
                bg = "rgba(108,117,125,0.12)"

            rec.facture_tag = (
                f"<span style='display:inline-block;padding:2px 8px;border-radius:12px;"
                f"font-weight:600;background:{bg};color:{color};'>"
                f"{label}"
                f"</span>"
            )

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
    # ------------------------------------------------------------
    # CONTRAINTE D’UNICITÉ
    # ------------------------------------------------------------
    @api.constrains('chq')
    def _check_exactly_seven_digits(self):
        for rec in self:
            if rec.chq is not None:
                if len(str(abs(rec.chq))) != 7:
                    raise ValidationError("Le chèque doit contenir exactement 7 chiffres.")


    @api.constrains('chq')
    def _check_unique_chq(self):
        for rec in self:
            if rec.chq:
                existing = self.search([
                    ('id', '!=', rec.id),
                    ('chq', '=', rec.chq),
                ], limit=1)

                if existing:
                    raise ValidationError("Ce numéro de chèque existe déjà. Il doit être unique.")

                
    @api.constrains('name')
    def _check_facture_format(self):
        for rec in self:
            facture = rec.name or ""

            # Conditions autorisées :
            cond_f = facture.startswith("F/")
            cond_m = facture == "M"
            cond_b = facture == "Bureau"

            if not (cond_f or cond_m or cond_b):
                raise ValidationError(
                    "Valeur facture invalide.\n"
                    "Elle doit être :\n"
                    "- exactement 'M', ou\n"
                    "- exactement 'Bureau', ou\n"
                    "- commencer par 'F/'."
                )


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