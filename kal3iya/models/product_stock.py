from odoo import models, fields, api
from odoo.exceptions import UserError

class ProductStock(models.Model):
    _name = 'kal3iya.stock'
    _description = 'Stock réel'

    name = fields.Char(string='Nom du produit', required=True)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
    ], string='Frigo', tracking=True)
    
    quantity = fields.Float(string='Quantité disponible', default=0)
    price = fields.Float(string='Prix d’achat')
    weight = fields.Float(string='Poids (kg)', required=True)
    tonnage = fields.Float(string='Tonnage (Kg)')
    calibre = fields.Char(string='Calibre')
    ste_id = fields.Many2one('kal3iya.ste', string='Société', optional=True)
    provider_id = fields.Many2one('kal3iya.provider', string='Fournisseur', optional=True)
    active = fields.Boolean(string='Actif', default=True)
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)


    # ------------------------------------------------------------
    # AFFICHAGE
    # ------------------------------------------------------------
    display_name = fields.Char(string='Nom affiché', compute='_compute_display_name', store=False)

    @api.depends('name', 'lot', 'dum', 'frigo')
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

    @api.model
    def update_stock_archive_status(self):
        """Archive ou désarchive automatiquement les produits selon leur quantité"""
        # Archiver les produits avec 0 ou moins
        zero_stocks = self.search([('quantity', '<=', 0), ('active', '=', True)])
        zero_stocks.write({'active': False})

        # Réactiver les produits qui reviennent en stock
        active_stocks = self.search([('quantity', '>', 0), ('active', '=', False)])
        active_stocks.write({'active': True})