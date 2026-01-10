from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Kal3iyaStockMove(models.Model):
    _name = 'kal3iya.stock.move'
    _description = 'Movement Ledger'
    _order = 'date desc, id desc'

    product_id = fields.Many2one('kal3iya.stock.product', string='Produit', required=True, ondelete='restrict')
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
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
    ], string='Garage', required=True)
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_kal3iya', 'Stock Kal3iya'),
    ], string='Frigo')
    
    qty = fields.Float(string='Quantité', required=True)
    
    move_type = fields.Selection([
        ('entry', 'Entrée'),
        ('exit', 'Sortie'),
        ('cancel_entry', 'Annulation Entrée'),
        ('cancel_exit', 'Annulation Sortie'),
        ('adjustment', 'Ajustement'),
    ], string='Type de mouvement', required=True)
    
    state = fields.Selection([
        ('done', 'Fait'),
    ], string='État', default='done', required=True)
    
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    reference = fields.Char(string='Référence')
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.user)

    # Origin Tracking
    res_model = fields.Char(string='Modèle d\'Origine', readonly=True)
    res_id = fields.Integer(string='ID d\'Origine', readonly=True)

    # Optional fields for reporting
    price_purchase = fields.Float(string='Prix Achat')
    price_sale = fields.Float(string='Prix Vente')
    weight = fields.Float(string='Poids (Kg)')
    calibre = fields.Char(string='Calibre')
    
    client_id = fields.Many2one('kal3iya.stock.client', string='Client')
    provider_id = fields.Many2one('kal3iya.stock.provider', string='Fournisseur')
    driver_id = fields.Many2one('kal3iya.stock.driver', string='Chauffeur')
    ste_id = fields.Many2one('kal3iya.stock.ste', string='Société')

    def unlink(self):
        raise UserError(_("Stock movements cannot be deleted. Use reversal moves instead."))
