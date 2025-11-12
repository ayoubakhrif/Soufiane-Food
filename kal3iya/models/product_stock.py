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
    
    name = fields.Char(string='Nom du produit', required=True)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
    ], string='Frigo', tracking=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Stock', tracking=True)
    quantity = fields.Float(string='Quantité disponible', default=0)
    price = fields.Float(string='Prix d’achat')
    weight = fields.Float(string='Poids (kg)', required=True)
    tonnage = fields.Float(string='Tonnage (Kg)')
    calibre = fields.Char(string='Calibre')
    ste_id = fields.Many2one('kal3iya.ste', string='Société', optional=True)
    provider_id = fields.Many2one('kal3iya.provider', string='Fournisseur', optional=True)
    active = fields.Boolean(string='Actif', default=True)
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)

    _order = 'name asc, quantity asc'


    # ------------------------------------------------------------
    # AFFICHAGE
    # ------------------------------------------------------------
    display_name = fields.Char(string='Nom affiché', compute='_compute_display_name', store=False)

    @api.depends('name', 'lot', 'dum', 'frigo', 'ville')
    def _compute_display_name(self):
        """Construit le texte affiché dans les menus déroulants"""
        for rec in self:
            frigo_label = dict(self._fields['frigo'].selection).get(rec.frigo, rec.frigo or '')
            rec.display_name = f"{rec.name} – Lot {rec.lot} – DUM {rec.dum} – {frigo_label}"

    def name_get(self):
        """Afficher: Produit_lot_dum_frigo"""
        result = []
        for record in self:
            frigo_label = dict(self._fields['frigo'].selection).get(record.frigo, record.frigo or '')
            name = f"{record.name}_{record.lot}_{record.dum}_{frigo_label}"
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
        """
        Recalcule la quantité disponible :
        Quantité stock = Entrée réelle + Retours - Sorties
        """
        for stock in self:
            # 🔹 Entrée d’origine (state='entree')
            origin_entry = stock.entry_id
            origin_qty = origin_entry.quantity if origin_entry and origin_entry.state == 'entree' else 0.0

            # 🔹 Retours sur la même combinaison
            returns = self.env['kal3iyaentry'].sudo().search([
                ('state', '=', 'retour'),
                ('lot', '=', stock.lot),
                ('dum', '=', stock.dum),
                ('frigo', '=', stock.frigo),
                ('ville', '=', stock.ville),
            ])
            qty_returns = sum(r.quantity for r in returns)

            # 🔹 Sorties liées à cette ligne
            sorties = self.env['kal3iyasortie'].sudo().search([('entry_id', '=', stock.id)])
            qty_sorties = sum(s.quantity for s in sorties)

            # 🔹 Quantité finale
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