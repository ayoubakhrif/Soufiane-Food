from odoo import models, fields, api

class CasaStockOrder(models.Model):
    _name = 'casa_field.stock.order'
    _description = 'Commande de Chargement'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='Nouveau')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    commercial_id = fields.Many2one('casa_field.stock.agent', string='Commercial', required=True, domain=[('role', '=', 'commercial')])
    client_id = fields.Many2one('casa_field.stock.client', string='Client', required=True)
    state = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Prepare')
    ], string='Statut', default='pending', required=True)
    
    line_ids = fields.One2many('casa_field.stock.order.line', 'order_id', string='Lignes de Commande')

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa_field.stock.order') or 'Nouveau'
        return super(CasaStockOrder, self).create(vals)


class CasaStockOrderLine(models.Model):
    _name = 'casa_field.stock.order.line'
    _description = 'Ligne de Commande de Chargement'

    order_id = fields.Many2one('casa_field.stock.order', string='Commande', required=True, ondelete='cascade')
    product_id = fields.Many2one('casa_field.stock.product', string='Produit', required=True)
    quantity = fields.Float(string='Quantite (Unites)', required=True, default=1.0)
    weight = fields.Float(string='Poids Unitaire (Kg)', required=True, default=0.0)
    tonnage = fields.Float(string='Tonnage Total (Kg)', compute='_compute_tonnage', store=True)
    note = fields.Text(string='Note Specifique')

    @api.depends('quantity', 'weight')
    def _compute_tonnage(self):
        for line in self:
            line.tonnage = line.quantity * line.weight
