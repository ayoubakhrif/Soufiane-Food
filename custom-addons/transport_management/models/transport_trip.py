from odoo import models, fields, api

class TransportTrip(models.Model):
    _name = 'transport.trip'
    _description = 'Transport Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date = fields.Date(string='Date de voyage', required=True, default=fields.Date.context_today)
    driver = fields.Char(string='Chauffeur', required=True, tracking=True)
    client = fields.Char(string='Client', required=True, tracking=True)
    
    trip_type = fields.Selection([
        ('tanger_med', 'Tanger Med'),
        ('soufiane', 'Soufiane'),
        ('la_zone', 'La zone'),
        ('client', 'Client'),
        ('mestapha', 'Mestapha'),
    ], string='Type de voyage', tracking=True)
    
    movement = fields.Selection([
        ('return', 'Retour'),
        ('entry', 'Entrée'),
    ], string='Movement', tracking=True)
    charge_fuel = fields.Float(string='Gazoil', tracking=True)
    charge_driver = fields.Float(string='Déplacement Chauffeur', tracking=True)
    charge_adblue = fields.Float(string='AdBlue', tracking=True)
    charge_mixed = fields.Float(string='Mixe (A préciser sur commentaire)', tracking=True)
    note = fields.Text(string='Commentaire (Mixe)')
    going_price = fields.Float(string='Prix allée', tracking=True)
    returning_price = fields.Float(string='Prix de retour', tracking=True)
    profit = fields.Float(
        string='Bénéfice',
        compute='_compute_profit',
        store=True,
        tracking=True
    )
    is_paid = fields.Boolean(string='Payé', default=False, tracking=True)
    total_amount = fields.Float(
        string='Montant total',
        compute='_compute_total_amount',
        store=True,
        tracking=True
    )

    def action_confirm_paid(self):
        for record in self:
            record.is_paid = True

    def action_set_unpaid(self):
        for record in self:
            record.is_paid = False

    @api.depends(
        'charge_fuel',
        'charge_driver',
        'charge_adblue',
        'charge_mixed'
    )
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = (
                (record.charge_fuel or 0.0) +
                (record.charge_driver or 0.0) +
                (record.charge_adblue or 0.0) +
                (record.charge_mixed or 0.0)
            )

    @api.depends('going_price', 'returning_price', 'total_amount')
    def _compute_profit(self):
        for rec in self:
            rec.profit = rec.going_price + rec.returning_price - rec.total_amount