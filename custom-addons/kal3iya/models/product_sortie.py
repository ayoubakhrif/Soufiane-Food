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
        tracking=True,
        ondelete='restrict', index=True
    )

    lot = fields.Char(string='Lot', related='entry_id.lot', store=True, readonly=True)
    dum = fields.Char(string='DUM', related='entry_id.dum', store=True, readonly=True)
    product_id = fields.Many2one(
        'kal3iya.product', 
        string='Produit',
        related='entry_id.product_id', 
        store=True, 
        readonly=True
    )
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
    quantity = fields.Float(string='Qté', required=True, tracking=True, group_operator="sum")
    selling_price = fields.Float(string='Prix de vente', required=True, tracking=True)
    date_exit = fields.Date(string='Date de sortie', required=True, tracking=True)
    tonnage = fields.Float(string='Tonnage(Kg)', compute='_compute_tonnage', store=True, readonly=True)
    price = fields.Float(string='Prix d’achat', related='entry_id.price', readonly=True)
    mt_achat = fields.Float(string='Mt.Achat', compute='_compute_mt_achat', store=True)
    mt_vente = fields.Float(string='Mt.Vente', compute='_compute_mt_vente', store=True)
    diff = fields.Float(string='Différence', compute='_compute_diff', store=True, group_operator="sum")
    driver_id = fields.Many2one('kal3iya.driver', string='Chauffeur', tracking=True)
    cellphone = fields.Char(string='Téléphone', related='driver_id.phone', readonly=True)
    client_id = fields.Many2one('kal3iya.client', tracking=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
        ('stock_casa', 'Stock'),
    ], string='Stock', tracking=True, store=True)
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock'),
    ], string='Frigo', related='entry_id.frigo', store=True, readonly=False, tracking=True)
    charge_transport = fields.Float(string='Main d’oeuvre', compute='_compute_charge_transport', store=True)
    image_1920 = fields.Image(string="Image", related='entry_id.image_1920', readonly=True, store=False)
    drive_file_url = fields.Char(string="Lien Google Drive", readonly=True, copy=False)
    drive_file_id = fields.Char(string="ID Fichier Drive", readonly=True, copy=False)
    benif_perte = fields.Html(string='Bénéfice/ perte', compute='_compute_benif_perte', sanitize=False)
    week = fields.Char(string='Semaine', compute='_compute_week', store=True)
    selling_price_final = fields.Float(string="Prix final", tracking=True)
    tonnage_final = fields.Float(string="Tonnage final", tracking=True)
    price_gap = fields.Float(string="Écart prix", compute="_compute_gaps", store=True)
    tonnage_gap = fields.Float(string="Écart tonnage", compute="_compute_gaps", store=True)
    mt_vente_final = fields.Float(string='Mt.Vente', compute='_compute_mt_vente_final', store=True)

    # ------------------------------------------------------------
    # BADGE VISUEL
    # ------------------------------------------------------------
    @api.depends('diff')
    def _compute_benif_perte(self):
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
    # Copier valeurs finaux
    # ------------------------------------------------------------
    @api.model
    def create(self, vals):
        # 1️⃣ Contrôle de stock avant création
        stock = self.env['kal3iya.stock'].browse(vals.get('entry_id'))
        if stock and vals.get('quantity', 0.0) > stock.quantity:
            raise UserError(
                f"Stock insuffisant: demande={vals.get('quantity')} > disponible={stock.quantity}."
            )

        # 2️⃣ Pré-remplir le prix final si non fourni
        if 'selling_price_final' not in vals and vals.get('selling_price'):
            vals['selling_price_final'] = vals['selling_price']

        # 3️⃣ Création de l'enregistrement
        rec = super().create(vals)

        # 4️⃣ Après création, tonnage est calculé → on peut copier tonnage_final
        if not rec.tonnage_final:
            rec.tonnage_final = rec.tonnage

        # 5️⃣ Recalcul du stock restant
        if stock:
            stock.recompute_qty()

        return rec

    def action_open_popup(self):
        """Ouvre le popup de modification"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modifier les valeurs finales',
            'res_model': 'kal3iyasortie',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('kal3iya.view_kal3iya_sortie_popup').id,  # Remplacez 'votre_module' par le nom de votre module
            'target': 'new',
            'context': dict(self.env.context),
        }
    
    def action_save_and_close(self):
        """Sauvegarde et ferme le popup (rafraîchit automatiquement la vue parent)"""
        # Les modifications sont déjà sauvegardées automatiquement par Odoo
        # On ferme juste le popup et la vue parent se rafraîchit automatiquement
        return {'type': 'ir.actions.act_window_close'}
    
    @api.onchange('ville')
    def _onchange_ville(self):
        """Filtrer le stock selon la ville choisie."""
        if self.ville:
            return {
                'domain': {
                    'entry_id': [('ville', '=', self.ville)]
                }
            }
        else:
            return {
                'domain': {
                    'entry_id': []
                }
            }


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

    @api.depends('price', 'tonnage')
    def _compute_mt_achat(self):
        for record in self:
            record.mt_achat = record.price * record.tonnage if record.price and record.tonnage else 0.0

    @api.depends('selling_price', 'tonnage')
    def _compute_mt_vente(self):
        for record in self:
            record.mt_vente = record.selling_price * record.tonnage if record.selling_price and record.tonnage else 0.0

    @api.depends('mt_achat', 'mt_vente')
    def _compute_diff(self):
        for record in self:
            record.diff = record.mt_vente - record.mt_achat

    @api.depends('date_exit')
    def _compute_week(self):
        for record in self:
            if record.date_exit:
                record.week = record.date_exit.strftime("%Y-W%W")
            else:
                record.week = False

    @api.depends('selling_price', 'selling_price_final', 'tonnage', 'tonnage_final')
    def _compute_gaps(self):
        for rec in self:
            rec.price_gap = (rec.selling_price_final or rec.selling_price) - rec.selling_price
            rec.tonnage_gap = (rec.tonnage_final or rec.tonnage) - rec.tonnage

    @api.depends('selling_price', 'selling_price_final', 'tonnage', 'tonnage_final')
    def _compute_mt_vente_final(self):
        for rec in self:
            # Si aucun changement → garder la valeur originale
            if not rec.selling_price_final and not rec.tonnage_final:
                rec.mt_vente_final = rec.mt_vente
                continue

            price = rec.selling_price_final or rec.selling_price
            tonnage = rec.tonnage_final or rec.tonnage

            rec.mt_vente_final = price * tonnage


    # ------------------------------------------------------------
    # AFFICHAGE
    # ------------------------------------------------------------
    display_name = fields.Char(
        string='Nom affiché', 
        compute='_compute_display_name', 
        store=False
    )

    @api.depends('client_id', 'product_id', 'lot', 'dum', 'quantity')
    def _compute_display_name(self):
        """Construit le texte affiché dans les menus déroulants"""
        for rec in self:
            client = rec.client_id.name or ''
            produit = rec.product_id.name or ''
            lot = rec.lot or ''
            dum = rec.dum or ''
            qty = rec.quantity or 0
            rec.display_name = f"{client} - {produit} - Lot {lot} - DUM {dum} - Qté {qty}"

    def name_get(self):
        """Personnaliser le nom affiché dans les listes déroulantes"""
        result = []
        for rec in self:
            client = rec.client_id.name or ''
            produit = rec.product_id.name or ''
            lot = rec.lot or ''
            dum = rec.dum or ''
            qty = rec.quantity or 0
            name = f"{client} - {produit} - Lot {lot} - DUM {dum} - Qté {qty}"
            result.append((rec.id, name))
        return result

    # ------------------------------------------------------------
    # CRUD OVERRIDES
    # ------------------------------------------------------------
    
    
    def write(self, vals):
        # 1️⃣ Vérification de stock (avant écriture)
        if 'quantity' in vals:
            for rec in self:
                old_qty = rec.quantity
                new_qty = vals['quantity']
                diff = new_qty - old_qty

                if diff > 0 and diff > rec.entry_id.quantity:
                    raise UserError(
                        f"Stock insuffisant : demande +{diff} > disponible {rec.entry_id.quantity}."
                    )

        # 2️⃣ Écriture normale
        res = super().write(vals)

        # 3️⃣ Recalcul du stock une seule fois par entrée
        self.mapped('entry_id').recompute_qty()

        return res



    def unlink(self):
        # Retours liés ? Si tu gères des retours par lien Many2one, bloque ici.
        # Exemple: returns = self.env['kal3iyaentry'].search_count([('return_id', 'in', self.ids)]) > 0
        # if returns: raise UserError("Supprimer d’abord les retours liés.")
        stocks = self.mapped('entry_id')
        res = super().unlink()
        stocks.recompute_qty()
        return res