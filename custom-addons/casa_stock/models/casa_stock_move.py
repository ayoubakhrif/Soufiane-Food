from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CasaStockMove(models.Model):
    _name = 'casa.stock.move'
    _description = 'Movement Ledger'
    _order = 'date desc, id desc'

    product_id = fields.Many2one('casa.product', string='Produit', required=True, ondelete='restrict')
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    scan_dum = fields.Char(string='Scan DUM (Drive)')
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', required=True)
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo')
    
    qty = fields.Float(string='Quantité', required=True)
    
    move_type = fields.Selection([
        ('entry', 'Entrée'),
        ('exit', 'Sortie'),
        ('return', 'Retour Client'),
        ('cancel_entry', 'Annulation Entrée'),
        ('cancel_exit', 'Annulation Sortie'),
        ('cancel_return', 'Annulation Retour'),
        ('adjustment', 'Ajustement'),
    ], string='Type de mouvement', required=True)
    
    state = fields.Selection([
        ('done', 'Fait'),
    ], string='État', default='done', required=True)
    
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    reference = fields.Char(string='Référence')
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.user)
    stock_soufiane = fields.Boolean(string='Stock Soufiane', default=False)

    # Origin Tracking
    res_model = fields.Char(string='Modèle d\'Origine', readonly=True)
    res_id = fields.Integer(string='ID d\'Origine', readonly=True)

    # Optional fields for reporting
    price_purchase = fields.Float(string='Prix Achat')
    price_sale = fields.Float(string='Prix Vente')
    weight = fields.Float(string='Poids (Kg)')

    @api.constrains('price_sale')
    def _check_price_sale(self):
        for rec in self:
            if rec.move_type in ('exit', 'return') and rec.price_sale <= 0:
                 raise UserError(_("Le prix de vente doit être strictement positif (%s).") % rec.product_id.name)
    calibre = fields.Char(string='Calibre')
    
    client_id = fields.Many2one('casa.client', string='Client')
    provider_id = fields.Many2one('casa.provider', string='Fournisseur')
    driver_id = fields.Many2one('casa.driver', string='Chauffeur')
    ste_id = fields.Many2one('casa.ste', string='Société')

    # def unlink(self):
    #     raise UserError(_("Stock movements cannot be deleted. Use reversal moves instead."))

