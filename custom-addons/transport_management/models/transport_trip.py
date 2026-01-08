from odoo import models, fields, api

class TransportTrip(models.Model):
    _name = 'transport.trip'
    _description = 'Transport Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date = fields.Date(string='Trip Date', required=True, default=fields.Date.context_today)
    driver = fields.Char(string='Chauffeur', required=True, tracking=True)
    client = fields.Many2one(string='Client', required=True, tracking=True)
    
    trip_type = fields.Selection([
        ('tanger_med', 'Tanger Med'),
        ('soufiane', 'Soufiane'),
        ('la_zone', 'La zone'),
        ('client', 'Client'),
        ('mestapha', 'Mestapha'),
    ], string='Type de voyage', tracking=True)
    
    movement = fields.Selection([
        ('return', 'Retour'),
        ('departure', 'Departure'),
        ('entry', 'Entry'),
    ], string='Movement', tracking=True)
    
    charge_type = fields.Selection([
        ('fuel', 'Gasoil'),
        ('driver_allowance', 'Déplacement chauffeur'),
        ('adblue', 'AdBlue'),
        ('mixed', 'Mixte'),
    ], string='Charge Type', tracking=True)
    
    amount = fields.Float(string='Amount', tracking=True)
    note = fields.Text(string='Note')
    
    is_paid = fields.Boolean(string='Paid', default=False, tracking=True)

    def action_confirm_paid(self):
        for record in self:
            record.is_paid = True

    def action_set_unpaid(self):
        for record in self:
            record.is_paid = False
