from odoo import models, fields, api
from odoo.exceptions import UserError

class ProductStock(models.Model):
    _name = 'kal3iya.stock'
    _description = 'Stock réel'

    entry_id = fields.Many2one(
        'kal3iyaentry',
        string='Entrée d’origine',
        ondelete='restrict',
        help="Entrée de stock à l'origine de cette ligne",
    )
    
    product_id = fields.Many2one('kal3iya.product', string='Nom du produit', optional=True, store=True)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock'),
    ], string='Frigo', tracking=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Stock', tracking=True)
    quantity = fields.Float(string='Quantité disponible', default=0, store=True)
    price = fields.Float(string='Prix d’achat')
    weight = fields.Float(string='Poids (kg)', required=True)
    tonnage = fields.Float(string='Tonnage (Kg)', compute='_compute_tonnage', store=True, group_operator="sum")
    mt_achat = fields.Float(string='Mt.Achat', compute='_compute_mt_achat', store=True, group_operator="sum")
    calibre = fields.Char(string='Calibre')
    ste_id = fields.Many2one('kal3iya.ste', string='Société', optional=True)
    provider_id = fields.Many2one('kal3iya.provider', string='Fournisseur', optional=True)
    active = fields.Boolean(string='Actif', default=True)
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)
    qty_total_group = fields.Float(
        compute="_compute_qty_total_group",
        string="Total Quantité",
        store=False
    )

    _order = 'product_id asc, quantity asc'

    @api.depends('product_id')
    def _compute_qty_total_group(self):
        for rec in self:
            total = sum(self.search([('product_id', '=', rec.product_id)]).mapped('quantity'))
            rec.qty_total_group = total
    # ------------------------------------------------------------
    # AFFICHAGE
    # ------------------------------------------------------------
    display_name = fields.Char(string='Nom affiché', compute='_compute_display_name', store=False)

    @api.depends('product_id', 'lot', 'dum', 'frigo', 'ville', 'quantity', 'price')
    def _compute_display_name(self):
        """Construit le texte affiché dans les menus déroulants"""
        for rec in self:
            frigo_label = dict(self._fields['frigo'].selection).get(rec.frigo, rec.frigo or '')
            rec.display_name = f"{rec.product_id.name} – Lot {rec.lot} – DUM {rec.dum} – {frigo_label} - Qté{rec.quantity} - prix{rec.price}"

    def name_get(self):
        """Afficher: Produit_lot_dum_frigo"""
        result = []
        for record in self:
            product = record.product_id.name or ''
            frigo_label = dict(self._fields['frigo'].selection).get(record.frigo, record.frigo or '')
            name = f"{product}_{record.lot}_{record.dum}_{frigo_label}_{record.quantity}_prix:{record.price}"
            result.append((record.id, name))
        return result

    # ------------------------------------------------------------
    # RESTRICTION SUR SUPPRESSION
    # ------------------------------------------------------------
    def unlink(self):
        """Empêche la suppression si des sorties existent."""
        for rec in self:
            sorties = self.env['kal3iyasortie'].sudo().search_count([('entry_id', '=', rec.id)])
            if sorties:
                raise UserError(
                    f"Impossible de supprimer le stock '{rec.display_name}' : "
                    f"des sorties sont encore liées."
                )
        return super().unlink()
    
    # ------------------------------------------------------------
    # MISE À JOUR AUTOMATIQUE DE LA QUANTITÉ
    # ------------------------------------------------------------
    def recompute_qty(self):
        for stock in self:
            # Entrée d'origine
            origin_qty = stock.entry_id.quantity if stock.entry_id else 0.0

            # Retours DIRECTEMENT liés au stock
            returns = self.env['kal3iyaentry'].search([
                ('state', '=', 'retour'),
                ('stock_id', '=', stock.id),
            ])
            qty_returns = sum(returns.mapped('quantity'))

            # Sorties liées
            sorties = self.env['kal3iyasortie'].search([
                ('entry_id', '=', stock.id)
            ])
            qty_sorties = sum(sorties.mapped('quantity'))

            stock.quantity = origin_qty + qty_returns - qty_sorties


            # 🔹 Archivage automatique
            if stock.quantity <= 0 and stock.active:
                stock.active = False
            elif stock.quantity > 0 and not stock.active:
                stock.active = True

    @api.model
    def update_stock_archive_status(self):
        """Archive ou désarchive automatiquement les produits selon leur quantité"""
        # Archiver les produits avec 0 ou moins
        zero_stocks = self.search([('quantity', '<=', 0), ('active', '=', True)])
        zero_stocks.write({'active': False})

        # Réactiver les produits qui reviennent en stock
        active_stocks = self.search([('quantity', '>', 0), ('active', '=', False)])
        active_stocks.write({'active': True})

    @api.depends('quantity', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.quantity * rec.weight if rec.quantity and rec.weight else 0.0
    
    @api.depends('price', 'tonnage')
    def _compute_mt_achat(self):
        for record in self:
            record.mt_achat = record.price * record.tonnage if record.price and record.tonnage else 0.0

    # filtrer sur ville et valeur rentrée
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Surcharge pour filtrer selon ville ET recherche textuelle.
        """
        args = args or []
        
        # Récupérer la ville depuis le contexte
        ville = self._context.get('ville_filter')
        
        if ville:
            args = args + [('ville', '=', ville)]
        
        # Ajouter filtre sur quantité disponible
        args = args + [('quantity', '>', 0)]
        
        # Si l'utilisateur tape quelque chose, chercher dans product_id.name
        if name:
            # Chercher les produits correspondants
            products = self.env['kal3iya.product'].search([('name', operator, name)])
            if products:
                args += [('product_id', 'in', products.ids)]
        
        # Rechercher les enregistrements
        stocks = self.search(args, limit=limit)
        
        return stocks.name_get()

    @api.model
    def action_recalculate_all_stock(self):
        """Action serveur : Recalculer tout le stock (même les archivés)"""
        # 1. Rechercher TOUS les stocks (actifs et archivés)
        all_stocks = self.with_context(active_test=False).search([])
        
        # 2. Lancer le re-calcul
        # (recompute_qty boucle déjà sur self, donc c'est optimisé)
        all_stocks.recompute_qty()
        
        # 3. Notification UI
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': f"Le stock a été recalculé pour {len(all_stocks)} enregistrements.",
                'type': 'success',
                'sticky': False,
            }
        }