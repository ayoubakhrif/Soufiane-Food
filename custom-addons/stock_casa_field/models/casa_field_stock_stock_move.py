from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CasaStockMove(models.Model):
    ste_id = fields.Integer(string='Ancienne Societe (A ignorer)')
    _name = 'casa_field.stock.move'
    _description = 'Movement Ledger'
    _order = 'date desc, id desc'

    product_id = fields.Many2one('casa_field.stock.product', string='Produit', required=True, ondelete='restrict')
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
        ('fenidek', 'Fenidek'),
    ], string='Garage', required=True)
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo')
    
    qty = fields.Float(string='QuantitÃ©', required=True)
    
    move_type = fields.Selection([
        ('entry', 'EntrÃ©e'),
        ('exit', 'Sortie'),
        ('cancel_entry', 'Annulation EntrÃ©e'),
        ('cancel_exit', 'Annulation Sortie'),
        ('adjustment', 'Ajustement'),
    ], string='Type de mouvement', required=True)
    
    state = fields.Selection([
        ('done', 'Fait'),
    ], string='Ã‰tat', default='done', required=True)
    
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    reference = fields.Char(string='RÃ©fÃ©rence')
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.user)

    # Origin Tracking
    res_model = fields.Char(string='ModÃ¨le d\'Origine', readonly=True)
    res_id = fields.Integer(string='ID d\'Origine', readonly=True)

    # Optional fields for reporting
    price_purchase = fields.Float(string='Prix Achat')

    weight = fields.Float(string='Poids (Kg)')
    calibre = fields.Char(string='Calibre')
    
    client_id = fields.Many2one('casa_field.stock.client', string='Client')
    driver_id = fields.Many2one('casa_field.stock.driver', string='Chauffeur')

    def unlink(self):
        if not self.env.user.has_group('casa_field_stock.group_manager'):
            raise UserError(_("Stock movements cannot be deleted. Use reversal moves instead."))
        return super(CasaStockMove, self).unlink()


