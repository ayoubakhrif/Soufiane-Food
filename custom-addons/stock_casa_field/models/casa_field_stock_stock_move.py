from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CasaStockMove(models.Model):
    _name = 'casa_field.stock.move'
    _description = 'Movement Ledger'
    _order = 'date desc, id desc'

    product_id = fields.Many2one('casa_field.stock.product', string='Produit', required=True, ondelete='restrict')
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo')
    
    qty = fields.Float(string='Quantite', required=True)
    
    move_type = fields.Selection([
        ('entry', 'Entree'),
        ('exit', 'Sortie'),
        ('cancel_entry', 'Annulation Entree'),
        ('cancel_exit', 'Annulation Sortie'),
        ('adjustment', 'Ajustement'),
    ], string='Type de mouvement', required=True)
    
    state = fields.Selection([
        ('done', 'Fait'),
        ('registered', 'Enregistré'),
    ], string='e‰tat', default='done', required=True)
    
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    reference = fields.Char(string='Reference')
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.user)

    # Origin Tracking
    res_model = fields.Char(string='Modele d\'Origine', readonly=True)
    res_id = fields.Integer(string='ID d\'Origine', readonly=True)

    # Optional fields for reporting
    price_purchase = fields.Float(string='Prix Achat')

    weight = fields.Float(string='Poids (Kg)')
    calibre = fields.Char(string='Calibre')
    
    client_id = fields.Many2one('casa_field.stock.client', string='Client')
    driver_id = fields.Many2one('casa_field.stock.driver', string='Chauffeur')



