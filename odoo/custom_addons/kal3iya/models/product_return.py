from odoo import models, fields, api

class Productreturn(models.Model):
    _name = 'kal3iyareturn'
    _description = 'Retour vers stock'

    name = fields.Char(string='Nom du produit', required=True)
    quantity = fields.Integer(string='Qté', required=True)
    date_return = fields.Date(string='Date de retour')
    lot = fields.Char(string='Lot', required=True)
    dum = fields.Char(string='DUM', required=True)
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
    ])
    weight = fields.Float(string='Poids (kg)', required=True)
    tonnage = fields.Float(string='Tonnage(Kg)', compute='_compute_tonnage', store=True)
    calibre = fields.Char(string='Calibre')
    driver_id = fields.Many2one('kal3iya.driver')
    cellphone = fields.Char(string='Téléphone', required=True)
    ste_id = fields.Char(string='Société', required=True)
    provider_id = fields.Many2one('kal3iya.provider')
    client_id = fields.Many2one('kal3iya.client')

    @api.depends('quantity', 'weight')
    def _compute_tonnage(self):
        for record in self:
            record.tonnage = record.quantity * record.weight if record.quantity and record.weight else 0.0
    
    @api.onchange('driver_id')
    def _onchange_driver_id(self):
        if self.driver_id:
            self.cellphone = self.driver_id.phone
        else:
            self.cellphone = False
